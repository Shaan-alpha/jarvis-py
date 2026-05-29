import re


def parse_reminder(query):

    query = query.lower()

    # remind me in 10 minutes to drink water

    pattern = (
        r"remind me in (\d+) minute[s]* to (.+)"
    )

    match = re.search(
        pattern,
        query
    )

    if match:

        minutes = int(
            match.group(1)
        )

        message = match.group(2)

        return {
            "minutes": minutes,
            "message": message
        }

    return None
