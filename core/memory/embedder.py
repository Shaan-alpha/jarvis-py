import logging
import os

# Silence noisy upstream loggers before fastembed imports them.
os.environ.setdefault(
    "HF_HUB_DISABLE_SYMLINKS_WARNING",
    "1"
)

logging.getLogger("httpx").setLevel(
    logging.WARNING
)

logging.getLogger("huggingface_hub").setLevel(
    logging.WARNING
)

# pyrefly: ignore [missing-import]
from fastembed import TextEmbedding


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

CACHE_DIR = "models/embeddings"


_text_embedder = TextEmbedding(
    model_name=MODEL_NAME,
    cache_dir=CACHE_DIR
)


def encode(texts):

    if isinstance(texts, str):

        texts = [texts]

    return list(
        _text_embedder.embed(texts)
    )
