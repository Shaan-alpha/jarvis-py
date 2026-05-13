from rapidfuzz import fuzz

from core.speech.engine import command


WAKE_WORDS = [
    "jarvis",
    "hey jarvis",
    "wake up jarvis",
    "jarvis wake up",
]


def is_similar(text, wake_word, threshold=75):

    similarity = fuzz.partial_ratio(
        text,
        wake_word
    )

    return similarity >= threshold


def detect_wake_word():

    query = command()

    if query == "none":

        return False

    print(f"[WAKE QUERY]: {query}")

    for wake_word in WAKE_WORDS:

        if is_similar(query, wake_word):

            print(f"Wake word detected: {wake_word}")

            return True

    return False