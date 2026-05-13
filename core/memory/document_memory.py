import os
import pickle

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


DOCS_PATH = "data/documents"

INDEX_PATH = "data/vector.index"

CHUNKS_PATH = "data/chunks.pkl"


_cache = {
    "index": None,
    "chunks": None
}


def _invalidate_cache():

    _cache["index"] = None
    _cache["chunks"] = None


def _encode_matrix(texts):

    vectors = encode(texts)

    return np.stack(vectors).astype(np.float32)


def read_pdf(path):

    reader = PdfReader(path)

    text = ""

    for page in reader.pages:

        text += page.extract_text() + "\n"

    return text


def chunk_text(text, chunk_size=500):

    return [
        text[i:i + chunk_size]
        for i in range(0, len(text), chunk_size)
    ]


def build_index():

    documents = []

    for file in os.listdir(DOCS_PATH):

        path = os.path.join(DOCS_PATH, file)

        if file.endswith(".pdf"):

            text = read_pdf(path)

            documents.extend(chunk_text(text))

    if not documents:

        print("No PDFs found to index.")
        return

    matrix = _encode_matrix(documents)

    index = faiss.IndexFlatIP(matrix.shape[1])

    index.add(matrix)

    faiss.write_index(index, INDEX_PATH)

    with open(CHUNKS_PATH, "wb") as file:

        pickle.dump(documents, file)

    _invalidate_cache()

    print(f"Indexed {len(documents)} chunks.")


def _load_index_and_chunks():

    if _cache["index"] is not None:

        return _cache["index"], _cache["chunks"]

    if not os.path.exists(INDEX_PATH):

        return None, None

    if not os.path.exists(CHUNKS_PATH):

        return None, None

    _cache["index"] = faiss.read_index(INDEX_PATH)

    with open(CHUNKS_PATH, "rb") as file:

        _cache["chunks"] = pickle.load(file)

    return _cache["index"], _cache["chunks"]


def search_documents(query, top_k=3):

    index, chunks = _load_index_and_chunks()

    if index is None:

        return []

    query_matrix = _encode_matrix([query])

    scores, indices = index.search(query_matrix, top_k)

    results = []

    for score, idx in zip(scores[0], indices[0]):

        if idx < 0 or idx >= len(chunks):

            continue

        if float(score) < DOCUMENT_SIMILARITY_THRESHOLD:

            continue

        results.append(chunks[idx])

    return results
