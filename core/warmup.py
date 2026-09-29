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


# A cold load of a multi-GB model — on a machine that has to page it in — takes
# minutes, not seconds. At 30s the warmup timed out on every start, so the first
# real query paid the model load anyway and the preload bought nothing. This runs
# on a daemon thread off the critical path, so the long wait costs nothing.
WARM_TIMEOUT = 180


def _post(url, json=None, timeout=None):
    """Seam for the warmup request. requests is imported here, not at module
    level, so importing this module stays cheap."""

    import requests

    return requests.post(url, json=json, timeout=timeout)


def _free_gb():
    """Free RAM in GiB (psutil imported lazily to keep this module cheap)."""

    import psutil

    return psutil.virtual_memory().available / 2 ** 30


def _warm_ollama():
    """Prime the LLM so the first ask_llm isn't a cold model load — unless RAM
    is short, where preloading only thrashes the machine (the first real query
    still loads it on demand)."""

    from config.settings import (
        LLM_KEEP_ALIVE,
        LLM_NUM_CTX,
        MODEL_MIN_FREE_GB,
        MODEL_NAME,
        OLLAMA_URL,
    )

    free = _free_gb()

    if free < MODEL_MIN_FREE_GB:

        raise RuntimeError(
            f"only {free:.1f} GiB free (< {MODEL_MIN_FREE_GB}); skipping the model preload"
        )

    _post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": "hi",
            "stream": False,
            "keep_alive": LLM_KEEP_ALIVE,
            "options": {"num_predict": 1, "num_ctx": LLM_NUM_CTX},
        },
        timeout=WARM_TIMEOUT,
    )


def _prime_request():
    """One-token request that makes Ollama load the model (errors ignored)."""

    from config.settings import LLM_KEEP_ALIVE, LLM_NUM_CTX, MODEL_NAME, OLLAMA_URL

    try:

        _post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": "hi",
                "stream": False,
                "keep_alive": LLM_KEEP_ALIVE,
                "options": {"num_predict": 1, "num_ctx": LLM_NUM_CTX},
            },
            timeout=WARM_TIMEOUT,
        )

    except Exception as e:

        logger.info(f"prime_model: {e}")


def prime_model():
    """Load the model in the background the moment the wake word fires, so the
    load overlaps with the user speaking instead of delaying the first answer
    (a cold load measured 13.5s). No RAM guard: a query is coming anyway."""

    thread = threading.Thread(target=_prime_request, daemon=True)

    thread.start()

    return thread


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
