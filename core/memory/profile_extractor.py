import re


# Clause boundaries: stop the capture here so "my name is tony and i like pizza"
# stores name="tony", not the whole tail of the sentence.
_CLAUSE_BREAKS = (" and ", " but ", " because ", " so ", ", ", "; ")

_VALUE_MAX = 60


def _trim_value(value):
    """Bound a greedy capture: cut at the first clause boundary, strip trailing
    punctuation, and cap the length so a runaway sentence can't fill the field."""

    value = value.strip()

    for sep in _CLAUSE_BREAKS:

        idx = value.find(sep)

        if idx != -1:

            value = value[:idx]

    return value.strip(" .,!?")[:_VALUE_MAX].strip()


def extract_personal_info(query):

    query = query.lower()

    patterns = [

        (
            r"my favorite programming language is (.+)",
            "favorite_language"
        ),

        (
            r"i am preparing for (.+)",
            "goal"
        ),

        (
            r"my name is (.+)",
            "name"
        ),

        (
            r"i like (.+)",
            "likes"
        ),
    ]

    for pattern, key in patterns:

        match = re.search(
            pattern,
            query
        )

        if match:

            value = _trim_value(match.group(1))

            if not value:

                return None

            return {
                "key": key,
                "value": value
            }

    return None
