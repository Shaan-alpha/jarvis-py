import os
import threading

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


MEMORY_PATH = os.path.join(
    str(user_data_dir()),
    "core",
    "memory",
    "semantic_memory.json"
)


_cache = {
    "memories": None,
    "embeddings": None
}

# Guards _cache: the HUD text-query path runs process_query on its own thread
# while the voice loop may also be mid-query, so cache reads/writes race.
_cache_lock = threading.Lock()


def _invalidate_cache():

    with _cache_lock:

        _cache["memories"] = None
        _cache["embeddings"] = None


def load_memories():

    return read_json(MEMORY_PATH, default=[])


def save_memory(user, assistant):

    memories = load_memories()

    memories.append({
        "user": user,
        "assistant": assistant
    })

    write_json_atomic(MEMORY_PATH, memories)

    _invalidate_cache()


def _get_embeddings():

    with _cache_lock:

        memories = _cache["memories"]

        if memories is None:

            memories = load_memories()

            _cache["memories"] = memories

            if memories:

                texts = [
                    f"{m['user']} {m['assistant']}"
                    for m in memories
                ]

                _cache["embeddings"] = np.stack(
                    encode(texts)
                )

            else:

                _cache["embeddings"] = None

        return memories, _cache["embeddings"]


def search_memory(query):

    memories, matrix = _get_embeddings()

    if not memories:

        return None

    query_vec = encode([query])[0]

    similarities = matrix @ query_vec

    best_index = int(similarities.argmax())

    best_score = float(similarities[best_index])

    if best_score < MEMORY_SIMILARITY_THRESHOLD:

        return None

    return memories[best_index]
