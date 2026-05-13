import os
# pyrefly: ignore [missing-import]
import faiss
import pickle

# pyrefly: ignore [missing-import]
from pypdf import PdfReader

from core.memory.embedder import (
    embedder
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


def read_pdf(path):

    reader = PdfReader(path)

    text = ""

    for page in reader.pages:

        text += page.extract_text() + "\n"

    return text


def chunk_text(
    text,
    chunk_size=500
):

    chunks = []

    for i in range(
        0,
        len(text),
        chunk_size
    ):

        chunks.append(
            text[i:i + chunk_size]
        )

    return chunks


def build_index():

    documents = []

    for file in os.listdir(DOCS_PATH):

        path = os.path.join(
            DOCS_PATH,
            file
        )

        if file.endswith(".pdf"):

            text = read_pdf(path)

            documents.extend(
                chunk_text(text)
            )

    embeddings = embedder.encode(
        documents
    )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(
        dimension
    )

    index.add(embeddings)

    faiss.write_index(
        index,
        INDEX_PATH
    )

    with open(
        CHUNKS_PATH,
        "wb"
    ) as file:

        pickle.dump(
            documents,
            file
        )

    _invalidate_cache()

    print(
        f"Indexed {len(documents)} chunks."
    )


def _load_index_and_chunks():

    if _cache["index"] is not None:

        return _cache["index"], _cache["chunks"]

    if not os.path.exists(INDEX_PATH):

        return None, None

    if not os.path.exists(CHUNKS_PATH):

        return None, None

    _cache["index"] = faiss.read_index(
        INDEX_PATH
    )

    with open(
        CHUNKS_PATH,
        "rb"
    ) as file:

        _cache["chunks"] = pickle.load(file)

    return _cache["index"], _cache["chunks"]


def search_documents(
    query,
    top_k=3
):

    index, chunks = (
        _load_index_and_chunks()
    )

    if index is None:

        return []

    query_embedding = embedder.encode(
        [query]
    )

    distances, indices = index.search(
        query_embedding,
        top_k
    )

    results = []

    for idx in indices[0]:

        if idx < len(chunks):

            results.append(
                chunks[idx]
            )

    return results
