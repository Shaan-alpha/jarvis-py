"""Long-term memory: only what the user explicitly asked Jarvis to remember.

Replaces the store that saved every chat turn (junk, duplicates and the
model's own wrong answers, all re-injected into later prompts). Facts are
deduplicated by meaning, capped, and searched by embedding similarity.
"""

import os
import threading
import time
import uuid

import numpy as np

from config.settings import (
    MEMORY_SIMILARITY_THRESHOLD
)

from core.memory.embedder import (
    encode
)

from core.paths import user_data_dir

from core.utils.jsonio import (
    read_json,
    write_json_atomic,
)


FACTS_PATH = os.path.join(str(user_data_dir()), "data", "memory", "facts.json")

MAX_FACTS = 300

# A new fact this close to a stored one replaces it instead of piling up.
DUPLICATE_SIMILARITY = 0.9

# "forget X" has to match a fact at least this well.
MATCH_SIMILARITY = 0.6


_cache = {
    "facts": None,
    "matrix": None,
}

_lock = threading.RLock()


def _now():

    return time.time()


def _vector(text):

    return np.asarray(encode([text])[0], dtype=np.float32)


def load_facts():

    stored = read_json(FACTS_PATH, default=[])

    if not isinstance(stored, list):

        return []

    return [
        fact for fact in stored
        if isinstance(fact, dict) and isinstance(fact.get("text"), str) and fact["text"].strip()
        and fact.get("id")
    ]


def _loaded():
    """(facts, matrix): read and encoded once, then kept in step with writes."""

    if _cache["facts"] is None:

        stored = load_facts()

        _cache["facts"] = stored

        _cache["matrix"] = (
            np.stack([np.asarray(v, dtype=np.float32) for v in encode([f["text"] for f in stored])])
            if stored else None
        )

    return _cache["facts"], _cache["matrix"]


def reset_cache():

    with _lock:

        _cache["facts"] = None

        _cache["matrix"] = None


def add_fact(text):
    """Remember `text`; a near-duplicate updates the stored fact."""

    text = (text or "").strip()

    if not text:

        return None

    with _lock:

        stored, matrix = _loaded()

        vector = _vector(text)

        if matrix is not None:

            scores = matrix @ vector

            best = int(scores.argmax())

            if float(scores[best]) >= DUPLICATE_SIMILARITY:

                stored[best]["text"] = text

                stored[best]["last_used"] = _now()

                matrix[best] = vector

                write_json_atomic(FACTS_PATH, stored)

                return dict(stored[best])

        fact = {"id": uuid.uuid4().hex, "text": text, "created": _now(), "last_used": _now()}

        stored.append(fact)

        matrix = vector[None, :] if matrix is None else np.vstack([matrix, vector])

        if len(stored) > MAX_FACTS:

            stale = min(range(len(stored)), key=lambda i: stored[i].get("last_used", 0))

            stored.pop(stale)

            matrix = np.delete(matrix, stale, axis=0)

        _cache["facts"], _cache["matrix"] = stored, matrix

        write_json_atomic(FACTS_PATH, stored)

        return dict(fact)


def search_facts(query, k=3):
    """Texts of up to `k` facts relevant to `query` (above the threshold)."""

    with _lock:

        stored, matrix = _loaded()

        if not stored:

            return []

        scores = matrix @ _vector(query)

        hits = [
            int(i) for i in np.argsort(-scores)[:k]
            if float(scores[int(i)]) >= MEMORY_SIMILARITY_THRESHOLD
        ]

        now = _now()

        for i in hits:

            stored[i]["last_used"] = now

        return [stored[i]["text"] for i in hits]


def find_fact(query):
    """The best-matching fact for `query`, or None below MATCH_SIMILARITY."""

    with _lock:

        stored, matrix = _loaded()

        if not stored:

            return None

        scores = matrix @ _vector(query)

        best = int(scores.argmax())

        return dict(stored[best]) if float(scores[best]) >= MATCH_SIMILARITY else None


def delete_fact(fact_id):

    with _lock:

        stored, matrix = _loaded()

        for i, fact in enumerate(stored):

            if fact["id"] == fact_id:

                stored.pop(i)

                _cache["matrix"] = np.delete(matrix, i, axis=0) if stored else None

                write_json_atomic(FACTS_PATH, stored)

                return True

        return False


def clear_facts():

    with _lock:

        write_json_atomic(FACTS_PATH, [])

        _cache["facts"], _cache["matrix"] = [], None


def all_facts():

    with _lock:

        stored, _ = _loaded()

        return [dict(fact) for fact in stored]
