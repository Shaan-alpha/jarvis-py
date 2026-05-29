import re


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

            value = match.group(1)

            return {
                "key": key,
                "value": value
            }

    return None
