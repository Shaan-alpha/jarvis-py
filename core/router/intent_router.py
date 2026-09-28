import re

from core.agent.registry import ToolCall

from core.text import normalize


_OPEN_APPS = {
    "open calculator": "calculator",
    "open notepad": "notepad",
    "open paint": "paint",
    "open edge": "edge",
}

_CLOSE_APPS = {
    "close calculator": "calculator",
    "close notepad": "notepad",
    "close paint": "paint",
}

_INCREASE_VOLUME = (
    "volume up",
    "increase volume",
    "increase the volume",
    "raise volume",
    "raise the volume",
)

_DECREASE_VOLUME = (
    "volume down",
    "decrease volume",
    "decrease the volume",
    "lower volume",
    "lower the volume",
)

_SYSTEM_STATUS = (
    "system status",
    "system condition",
    "condition of the system",
    "system info",
    "system information",
    "cpu usage",
    "battery status",
    "battery level",
    "battery percentage",
)

# Read-specific phrases. A "copy ... to clipboard" command matches NONE of these,
# so it falls through to the LLM write_clipboard (the resolver has no write path).
_CLIPBOARD_READ = (
    "read clipboard",
    "read my clipboard",
    "what's on my clipboard",
    "what's in my clipboard",
    "what's on the clipboard",
    "check clipboard",
    "show clipboard",
)

# Workspace file listing. Zero-arg, so it gets a fast-path; the arg-bearing fs
# tools (read/write/search) stay LLM-only. Phrases are multi-word and workspace
# specific, so they won't collide with open/close/volume triggers.
_LIST_FILES = (
    "list files",
    "list my files",
    "what files do i have",
    "what's in my workspace",
    "show my files",
    "show my workspace",
)

# Zero-arg tools matched on whole words, checked top to bottom (first match
# wins). Collapsing these into one table keeps resolve_keyword_tool flat
# instead of one if-branch per tool. The ToolCall instances are shared and never
# mutated (frozen dataclass; the executor only reads call.args). Whole-word matching
# keeps "mute" from firing on "commute".
_SUBSTRING_TOOLS = (
    (_INCREASE_VOLUME, ToolCall("increase_volume", {})),
    (_DECREASE_VOLUME, ToolCall("decrease_volume", {})),
    (("mute",), ToolCall("mute_volume", {})),
    (_SYSTEM_STATUS, ToolCall("system_status", {})),
    (_CLIPBOARD_READ, ToolCall("read_clipboard", {})),
    (_LIST_FILES, ToolCall("list_files", {})),
)


# Ordered: the longer, more specific trigger first so "search google for x"
# isn't swallowed by "google ".
_SEARCH_TRIGGERS = (
    "search google for",
    "search the web for",
    "search for",
    "google",
)

_SEARCH_PATTERNS = tuple(
    re.compile(rf"^\s*{re.escape(trigger)}\s+(.+?)[\s?.!]*$", re.IGNORECASE)
    for trigger in _SEARCH_TRIGGERS
)


def _word_pattern(phrase):
    """A regex matching `phrase` only as whole words ("mute" not "commute")."""

    return re.compile(rf"(?<!\w){re.escape(normalize(phrase))}(?!\w)")


_OPEN_APP_PATTERNS = tuple(
    (_word_pattern(phrase), name) for phrase, name in _OPEN_APPS.items()
)

_CLOSE_APP_PATTERNS = tuple(
    (_word_pattern(phrase), name) for phrase, name in _CLOSE_APPS.items()
)

_OPEN_GOOGLE_PATTERN = _word_pattern("open google")

_SUBSTRING_PATTERNS = tuple(
    (tuple(_word_pattern(p) for p in phrases), call)
    for phrases, call in _SUBSTRING_TOOLS
)


def _first_named(query, patterns, tool_name):

    for pattern, name in patterns:

        if pattern.search(query):

            return ToolCall(tool_name, {"name": name})

    return None


def _match_open_app(query, raw_query):

    return _first_named(query, _OPEN_APP_PATTERNS, "open_app")


def _match_open_google(query, raw_query):

    # The zero-arg homepage tool; checked before the search triggers.
    if _OPEN_GOOGLE_PATTERN.search(query):

        return ToolCall("open_google", {})

    return None


def _match_close_app(query, raw_query):

    return _first_named(query, _CLOSE_APP_PATTERNS, "close_app")


def _match_substring_tool(query, raw_query):
    """First zero-arg tool with a trigger phrase present as whole words."""

    for patterns, call in _SUBSTRING_PATTERNS:

        if any(p.search(query) for p in patterns):

            return call

    return None


def _search_term(trigger_pattern, query, raw_query):
    """The text after a search trigger, from the raw utterance when it matches
    there (keeps case: "search for Tony Stark" -> "Tony Stark")."""

    for text in (raw_query, query):

        match = trigger_pattern.match(text or "")

        if match and match.group(1).strip():

            return match.group(1).strip()

    return None


def _match_search(query, raw_query):

    for pattern in _SEARCH_PATTERNS:

        term = _search_term(pattern, query, raw_query)

        if term:

            return ToolCall("search_web", {"query": term})

    return None


# Checked in order; first match wins.
_MATCHERS = (
    _match_open_app,
    _match_open_google,
    _match_close_app,
    _match_substring_tool,
    _match_search,
)


def resolve_keyword_tool(query, raw_query=None):
    """Map a known command phrase to a registry ToolCall, or None.

    Deterministic and LLM-free (importable in CI). The query is normalized here
    too, so voice and typed input match the same tables. `raw_query` (the
    un-normalized utterance) is used where an argument's case matters.
    """

    if raw_query is None:

        raw_query = query

    query = normalize(query)

    for matcher in _MATCHERS:

        call = matcher(query, raw_query)

        if call is not None:

            return call

    return None
