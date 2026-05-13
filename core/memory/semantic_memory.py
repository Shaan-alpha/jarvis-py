import json
import os

import numpy as np

from config.settings import (
    MEMORY_SIMILARITY_THRESHOLD
)

from core.memory.embedder import (
    encode
)


MEMORY_PATH = (
    "core/memory/semantic_memory.json"
)


_cache = {
    "memories": None,
    "embeddings": None
}


def _invalidate_cache():

    _cache["memories"] = None
    _cache["embeddings"] = None


def load_memories():

    if not os.path.exists(MEMORY_PATH):

        return []

    with open(
        MEMORY_PATH,
        "r"
    ) as file:

        return json.load(file)


def save_memory(user, assistant):

    memories = load_memories()

    memories.append({
        "user": user,
        "assistant": assistant
    })

    with open(
        MEMORY_PATH,
        "w"
    ) as file:

        json.dump(
            memories,
            file,
            indent=4
        )

    _invalidate_cache()


def _get_embeddings():

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
