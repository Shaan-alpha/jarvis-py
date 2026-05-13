import os
# pyrefly: ignore [missing-import]
import faiss
import pickle

# pyrefly: ignore [missing-import]
from pypdf import PdfReader

# pyrefly: ignore [missing-import]
from sentence_transformers import (
    SentenceTransformer
)


DOCS_PATH = "data/documents"

INDEX_PATH = "data/vector.index"

CHUNKS_PATH = "data/chunks.pkl"


model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


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

    embeddings = model.encode(
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

    print(
        f"Indexed {len(documents)} chunks."
    )


def search_documents(
    query,
    top_k=3
):

    if not os.path.exists(INDEX_PATH):

        return []

    index = faiss.read_index(
        INDEX_PATH
    )

    with open(
        CHUNKS_PATH,
        "rb"
    ) as file:

        chunks = pickle.load(file)

    query_embedding = model.encode(
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