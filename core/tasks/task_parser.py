import re


# How many minutes one of each spoken unit is worth.
_UNIT_MINUTES = {
    "second": 1 / 60, "seconds": 1 / 60, "sec": 1 / 60, "secs": 1 / 60,
    "minute": 1, "minutes": 1, "min": 1, "mins": 1,
    "hour": 60, "hours": 60, "hr": 60, "hrs": 60,
}

_UNIT_GROUP = "|".join(_UNIT_MINUTES)

_AMOUNT_GROUP = r"\d+|a|an|half an?"

# "remind me in <amount> <unit> to <message>"
_FORWARD = re.compile(
    rf"remind me in ({_AMOUNT_GROUP}) ({_UNIT_GROUP}) to (.+)"
)

# "remind me to <message> in <amount> <unit>"  (non-greedy message)
_REVERSED = re.compile(
    rf"remind me to (.+?) in ({_AMOUNT_GROUP}) ({_UNIT_GROUP})\b"
)


def _amount_to_number(raw):
    """Turn a spoken amount ('5', 'a', 'an', 'half an') into a number."""

    if raw in ("a", "an"):

        return 1

    if raw.startswith("half"):

        return 0.5

    return int(raw)


def _minutes(amount_raw, unit):

    minutes = _amount_to_number(amount_raw) * _UNIT_MINUTES[unit]

    # Keep whole numbers as ints so spoken feedback says "30 minutes", not "30.0".
    if float(minutes).is_integer():

        return int(minutes)

    return round(minutes, 2)


def parse_reminder(query):
    """Parse a reminder phrase into {'minutes', 'message'} or None.

    Handles minutes/hours/seconds (and short forms), 'a'/'an'/'half an', and
    both word orders ('… in 5 minutes to X' and '… to X in 5 minutes').
    """

    query = query.lower()

    match = _FORWARD.search(query)

    if match:

        amount_raw, unit, message = match.group(1), match.group(2), match.group(3)

        return {"minutes": _minutes(amount_raw, unit), "message": message.strip()}

    match = _REVERSED.search(query)

    if match:

        message, amount_raw, unit = match.group(1), match.group(2), match.group(3)

        return {"minutes": _minutes(amount_raw, unit), "message": message.strip()}

    return None
