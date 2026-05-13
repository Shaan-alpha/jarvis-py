import json
import os

# pyrefly: ignore [missing-import]
from sentence_transformers import (
    SentenceTransformer
)

from sklearn.metrics.pairwise import (
    cosine_similarity
)

from config.settings import (
    MEMORY_SIMILARITY_THRESHOLD
)


MEMORY_PATH = (
    "core/memory/semantic_memory.json"
)

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


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


def search_memory(query):

    memories = load_memories()

    if not memories:

        return None

    memory_texts = [
        f"{m['user']} {m['assistant']}"
        for m in memories
    ]

    query_embedding = model.encode(
        [query]
    )

    memory_embeddings = model.encode(
        memory_texts
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