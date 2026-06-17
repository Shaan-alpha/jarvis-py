"""Warm-start: preload lazily-initialised components off the critical path.

The LLM (Ollama) and the embedding model load on first use, so the user's first
substantive query pays a cold-start. Warming them at startup on a daemon thread
moves that cost off the path of the first interaction. Each step is best-effort:
a failure is logged and skipped (the component just lazy-loads on demand later),
never fatal.

Vosk and the wake-word model are intentionally NOT warmed here: Vosk is only
needed when offline (warming it would load a model that may never be used), and
the wake-word model loads as the voice loop starts to listen anyway — warming it
on a parallel thread would just race that native load.
"""

import threading

from core.utils.logger import logger


def _warm_ollama():
    """Prime the LLM so the first ask_llm isn't a cold model load."""

    import requests

    from config.settings import MODEL_NAME, OLLAMA_URL

    requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": "hi",
            "stream": False,
            "options": {"num_predict": 1},
        },
        timeout=30,
    )


def _warm_embedder():
    """Load the embedding model so the first memory/document search isn't cold."""

    from core.memory.embedder import encode

    encode(["warmup"])


DEFAULT_TASKS = (
    ("ollama", _warm_ollama),
    ("embedder", _warm_embedder),
)


def run_warmup(tasks=DEFAULT_TASKS):
    """Run each (name, fn) preload, swallowing per-task errors. Returns the names
    that warmed successfully (for logging / tests)."""

    warmed = []

    for name, fn in tasks:

        try:

            fn()

            warmed.append(name)

            logger.info(f"warmup: {name} ready")

        except Exception as e:

            logger.warning(f"warmup: {name} failed ({e}); will lazy-load on demand")

    return warmed


def warm_start(tasks=DEFAULT_TASKS):
    """Kick off warmup on a daemon thread so startup isn't blocked. Returns the
    thread (mostly for tests)."""

    thread = threading.Thread(target=run_warmup, args=(tasks,), daemon=True)

    thread.start()

    return thread
