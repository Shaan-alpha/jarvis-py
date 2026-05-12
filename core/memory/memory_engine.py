import json
import os

MEMORY_FILE = os.path.join(
    os.path.dirname(__file__),
    "memory.json"
)


def load_memory():

    if not os.path.exists(MEMORY_FILE):
        return []

    try:
        with open(MEMORY_FILE, "r") as file:
            return json.load(file)

    except Exception:
        return []


def save_memory(user_input, assistant_response):

    if not user_input or not assistant_response:
        return

    memory = load_memory()

    memory.append({
        "user": user_input,
        "assistant": assistant_response
    })

    # Keep only recent chats
    memory = memory[-4:]

    with open(MEMORY_FILE, "w") as file:
        json.dump(memory, file, indent=6)