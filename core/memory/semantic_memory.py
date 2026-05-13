import json
import os

from sklearn.metrics.pairwise import (
    cosine_similarity
)

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

            _cache["embeddings"] = embedder.encode(
                memory_texts
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

    query_embedding = embedder.encode(
        [query]
    )

    similarities = cosine_similarity(
        query_embedding,
        memory_embeddings
    )[0]

    best_index = similarities.argmax()

    best_score = similarities[
        best_index
    ]

    if (
        best_score
        < MEMORY_SIMILARITY_THRESHOLD
    ):

        return None

    return memories[best_index]
