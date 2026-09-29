import os
import threading

# pyrefly: ignore [missing-import]
import faiss
import numpy as np

# pyrefly: ignore [missing-import]
from pypdf import PdfReader

from config.settings import (
    DOCUMENT_SIMILARITY_THRESHOLD
)

from core.memory.embedder import (
    encode
)

from core.paths import user_data_dir

from core.utils.jsonio import (
    read_json,
    write_json_atomic,
)

from core.utils.logger import (
    logger
)


DOCS_PATH = os.path.join(str(user_data_dir()), "data", "documents")

INDEX_PATH = os.path.join(str(user_data_dir()), "data", "vector.index")

# JSON, not pickle: loading a pickle from a user-writable folder runs whatever
# code it contains.
CHUNKS_PATH = os.path.join(str(user_data_dir()), "data", "chunks.json")

# {pdf name: [size, mtime]} of what the index was built from. A folder that no
# longer matches means the index is stale and must not be injected.
MANIFEST_PATH = os.path.join(str(user_data_dir()), "data", "documents_manifest.json")


_cache = {
    "index": None,
    "chunks": None,
    "manifest": None,
}

# Guards _cache against concurrent access (HUD text-query thread vs voice loop).
_cache_lock = threading.Lock()

_warned_stale = {"value": False}


def _invalidate_cache():

    with _cache_lock:

        _cache["index"] = None
        _cache["chunks"] = None
        _cache["manifest"] = None


def _encode_matrix(texts):

    vectors = encode(texts)

    return np.stack(vectors).astype(np.float32)


def read_pdf(path):

    reader = PdfReader(path)

    text = ""

    for page in reader.pages:

        # extract_text() returns None on some pages (scanned/empty); guard so
        # the concatenation doesn't raise TypeError mid-index.
        text += (page.extract_text() or "") + "\n"

    return text


def chunk_text(text, chunk_size=500):

    return [
        text[i:i + chunk_size]
        for i in range(0, len(text), chunk_size)
    ]


def _pdf_manifest():
    """{name: [size, mtime]} for every PDF in the documents folder."""

    if not os.path.isdir(DOCS_PATH):

        return {}

    manifest = {}

    for name in sorted(os.listdir(DOCS_PATH)):

        if name.lower().endswith(".pdf"):

            stat = os.stat(os.path.join(DOCS_PATH, name))

            manifest[name] = [stat.st_size, int(stat.st_mtime)]

    return manifest


def _clear_index():

    for path in (INDEX_PATH, CHUNKS_PATH, MANIFEST_PATH):

        if os.path.exists(path):

            os.remove(path)

    _invalidate_cache()


def build_index():
    """Index every PDF in DOCS_PATH. Returns (files, chunks); (0, 0) clears
    any old index so nothing stale is served."""

    # The documents folder may not exist yet on a fresh install.
    os.makedirs(DOCS_PATH, exist_ok=True)

    manifest = _pdf_manifest()

    chunks = []

    for name in manifest:

        text = read_pdf(os.path.join(DOCS_PATH, name))

        chunks.extend(
            {"file": name, "text": piece}
            for piece in chunk_text(text)
            if piece.strip()
        )

    if not chunks:

        _clear_index()

        return 0, 0

    matrix = _encode_matrix([chunk["text"] for chunk in chunks])

    index = faiss.IndexFlatIP(matrix.shape[1])

    index.add(matrix)

    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)

    faiss.write_index(index, INDEX_PATH)

    write_json_atomic(CHUNKS_PATH, chunks)

    write_json_atomic(MANIFEST_PATH, manifest)

    _invalidate_cache()

    return len(manifest), len(chunks)


def index_state():
    """'missing' (never built), 'stale' (folder changed) or 'ready'."""

    if not (os.path.exists(INDEX_PATH) and os.path.exists(CHUNKS_PATH)):

        return "missing"

    if read_json(MANIFEST_PATH, default=None) != _pdf_manifest():

        return "stale"

    return "ready"


def _load_index_and_chunks():

    manifest = _pdf_manifest()

    with _cache_lock:

        if _cache["index"] is not None and _cache["manifest"] == manifest:

            return _cache["index"], _cache["chunks"]

        _cache["index"] = _cache["chunks"] = _cache["manifest"] = None

        state = index_state()

        if state != "ready":

            if state == "stale" and not _warned_stale["value"]:

                logger.warning(
                    "Document index is stale (documents changed); not using it. "
                    "Say 'index my documents' or run build_memory.py."
                )

                _warned_stale["value"] = True

            return None, None

        _cache["index"] = faiss.read_index(INDEX_PATH)

        _cache["chunks"] = read_json(CHUNKS_PATH, default=[])

        _cache["manifest"] = manifest

        return _cache["index"], _cache["chunks"]


def search_chunks(query, top_k=3):
    """Best-matching chunks above the threshold: [{file, text, score}]."""

    index, chunks = _load_index_and_chunks()

    if index is None or not chunks:

        return []

    scores, indices = index.search(_encode_matrix([query]), top_k)

    results = []

    for score, idx in zip(scores[0], indices[0]):

        if idx < 0 or idx >= len(chunks):

            continue

        if float(score) < DOCUMENT_SIMILARITY_THRESHOLD:

            continue

        results.append({**chunks[idx], "score": float(score)})

    return results


def search_documents(query, top_k=3):

    return [chunk["text"] for chunk in search_chunks(query, top_k)]
