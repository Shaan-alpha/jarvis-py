# pyrefly: ignore [missing-import]
from sentence_transformers import (
    SentenceTransformer
)


MODEL_NAME = "all-MiniLM-L6-v2"


embedder = SentenceTransformer(MODEL_NAME)
