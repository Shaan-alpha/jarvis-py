"""Text normalisation shared by every input path.

Voice (STT) and typed (HUD) queries must hit the same command tables, so both
go through normalize() before matching. Stdlib only: any module may import it.
"""

import re


_QUOTES = str.maketrans({
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
})

# Anything that is not a word character, whitespace, '-' or '.', plus any '.'
# that is not sitting between two word characters ("notes.txt", "3.5" keep it).
_STRAY = re.compile(r"[^\w\s\-.]|(?<!\w)\.|\.(?!\w)")

_SPACES = re.compile(r"\s+")

# "notes dot txt" / "report dot p d f": spaced single letters, or one short word.
_SPOKEN_DOT = re.compile(r"\s+dot\s+((?:[a-z0-9]\s){1,4}[a-z0-9]\b|[a-z0-9]{1,5}\b)")


def normalize(text):
    """Lowercase, fold curly quotes, drop apostrophes ("what's" -> "whats"),
    keep '.' only inside words, turn other punctuation into spaces and collapse
    whitespace."""

    if not text:

        return ""

    text = text.translate(_QUOTES).lower().replace("'", "")

    text = _STRAY.sub(" ", text)

    return _SPACES.sub(" ", text).strip()


def spoken_filename(text):
    """'notes dot txt' -> 'notes.txt', 'report dot p d f' -> 'report.pdf'."""

    def _extension(match):

        return "." + match.group(1).replace(" ", "")

    return _SPOKEN_DOT.sub(_extension, (text or "").strip())


def plural(count, unit):
    """'1 minute', '5 minutes'."""

    return f"{count} {unit}" if count == 1 else f"{count} {unit}s"


def spoken_time(moment):
    """'4:05 PM' — no leading zero."""

    return moment.strftime("%I:%M %p").lstrip("0")


def spoken_date(moment):
    """'Monday, 28 September 2026'."""

    return f"{moment.strftime('%A')}, {moment.day} {moment.strftime('%B %Y')}"
