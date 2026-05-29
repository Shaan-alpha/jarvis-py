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

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

CACHE_DIR = "models/embeddings"


_text_embedder = None


def _get_embedder():
    global _text_embedder

    if _text_embedder is None:

        # Imported lazily so merely importing this module is cheap and does
        # not trigger a model download (keeps the core importable in CI).
        # pyrefly: ignore [missing-import]
        from fastembed import TextEmbedding

        _text_embedder = TextEmbedding(
            model_name=MODEL_NAME,
            cache_dir=CACHE_DIR,
        )

    return _text_embedder


def encode(texts):

    if isinstance(texts, str):

        texts = [texts]

    return list(
        _get_embedder().embed(texts)
    )
