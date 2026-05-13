import json
import os

import numpy as np

from config.settings import (
    MEMORY_SIMILARITY_THRESHOLD
)

from core.memory.embedder import (
    embedder
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


def _normalize(matrix):

    norms = np.linalg.norm(
        matrix,
        axis=1,
        keepdims=True
    )

    return matrix / np.clip(norms, 1e-12, None)


def _get_embeddings():

    memories = _cache["memories"]

    if memories is None:

        memories = load_memories()

        _cache["memories"] = memories

        if memories:

            memory_texts = [
                f"{m['user']} {m['assistant']}"
                for m in memories
            ]

            raw = embedder.encode(memory_texts)

            _cache["embeddings"] = _normalize(
                np.asarray(raw)
            )

        else:

            _cache["embeddings"] = None

    return memories, _cache["embeddings"]


def search_memory(query):

    memories, memory_embeddings = (
        _get_embeddings()
    )

    if not memories:

        return None

    query_vec = _normalize(
        np.asarray(embedder.encode([query]))
    )

    similarities = (
        memory_embeddings @ query_vec[0]
    )

    best_index = int(similarities.argmax())

    best_score = float(
        similarities[best_index]
    )

    if best_score < MEMORY_SIMILARITY_THRESHOLD:

        return None

    return memories[best_index]
