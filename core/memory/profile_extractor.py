import re


# Clause boundaries: stop the capture here so "my name is tony and i like pizza"
# stores name="tony", not the whole tail of the sentence.
_CLAUSE_BREAKS = (" and ", " but ", " because ", " so ", ", ", "; ")

_VALUE_MAX = 60

# Not facts: pronouns/determiners ("i like that") and requests ("i like to know
# the time") that the old greedy patterns stored as the user's likes.
_REJECT_VALUES = {
    "that", "it", "this", "those", "these", "them", "you", "him", "her",
    "me", "us", "so", "too", "very much", "a lot",
}

_REJECT_PREFIXES = (
    "to know", "to ask", "to see", "to hear", "to get", "to find",
    "if ", "when ", "how ", "what ", "why ", "where ", "who ", "the way",
)

_QUESTION = re.compile(
    r"^(?:what|whats|who|whos|where|when|why|how|do|does|did|can|could|would|should|is|are|will|shall)\b"
)

_FAVOURITE = re.compile(r"\bmy favou?rite ([a-z]+(?: [a-z]+)?) is (.+)")

_FAVOURITE_ALIASES = {"programming language": "language"}

_PATTERNS = (
    (re.compile(r"\bmy name is (.+)"), "name"),
    (re.compile(r"\bmy names (.+)"), "name"),
    (re.compile(r"^(?:please )?call me (.+)"), "name"),
    (re.compile(r"\bi live in (.+)"), "city"),
    (re.compile(r"\bmy birthday is (?:on )?(.+)"), "birthday"),
    (re.compile(r"\bi work as (?:a |an )?(.+)"), "job"),
    (re.compile(r"\b(?:i am|im) preparing for (.+)"), "goal"),
    (re.compile(r"^i (?:really )?(?:like|love) (.+)"), "likes"),
)


def _trim_value(value):
    """Bound a greedy capture: cut at the first clause boundary, strip trailing
    punctuation, and cap the length so a runaway sentence can't fill the field."""

    value = value.strip()

    for sep in _CLAUSE_BREAKS:

        idx = value.find(sep)

        if idx != -1:

            value = value[:idx]

    return value.strip(" .,!?")[:_VALUE_MAX].strip()


def _acceptable(value):

    return bool(value) and value not in _REJECT_VALUES and not value.startswith(_REJECT_PREFIXES)


def extract_personal_info(query):

    query = query.lower().strip()

    if _QUESTION.match(query) or query.endswith("?"):

        return None

    match = _FAVOURITE.search(query)

    if match:

        subject = _FAVOURITE_ALIASES.get(match.group(1), match.group(1))

        value = _trim_value(match.group(2))

        if not _acceptable(value):

            return None

        return {"key": "favourite_" + subject.replace(" ", "_"), "value": value}

    for pattern, key in _PATTERNS:

        match = pattern.search(query)

        if match:

            value = _trim_value(match.group(1))

            return {"key": key, "value": value} if _acceptable(value) else None

    return None
