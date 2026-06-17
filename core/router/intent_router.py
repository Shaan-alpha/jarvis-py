from core.agent.registry import ToolCall


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

# Ordered: "search google for " before "google " so the longer, more specific
# trigger wins (otherwise "google " would swallow it and mis-extract the term).
_SEARCH_TRIGGERS = (
    "search google for ",
    "search the web for ",
    "search for ",
    "google ",
)

# Zero-arg tools matched by substring containment, checked top to bottom (first
# match wins). Collapsing these into one table keeps resolve_keyword_tool flat
# instead of one if-branch per tool. The ToolCall instances are shared and never
# mutated (frozen dataclass; the executor only reads call.args). "mute" is a bare
# substring (so "commute" would also match — acceptable for a single-user setup).
_SUBSTRING_TOOLS = (
    (_INCREASE_VOLUME, ToolCall("increase_volume", {})),
    (_DECREASE_VOLUME, ToolCall("decrease_volume", {})),
    (("mute",), ToolCall("mute_volume", {})),
    (_SYSTEM_STATUS, ToolCall("system_status", {})),
    (_CLIPBOARD_READ, ToolCall("read_clipboard", {})),
    (_LIST_FILES, ToolCall("list_files", {})),
)


def _match_named_app(query, table, tool_name):
    """First phrase in `table` contained in `query` -> ToolCall(tool_name, name)."""

    for phrase, name in table.items():

        if phrase in query:

            return ToolCall(tool_name, {"name": name})

    return None


def _match_substring_tool(query):
    """First zero-arg substring tool whose any trigger is contained in `query`."""

    for phrases, call in _SUBSTRING_TOOLS:

        if any(p in query for p in phrases):

            return call

    return None


def _match_search(query, raw_query):
    """Web search: strip the trigger prefix to get the search term.

    The trigger is detected on the normalized `query`, but the term is pulled
    from `raw_query` so a typed search keeps its original case ("search for
    Tony Stark" -> "Tony Stark", not "tony stark").
    """

    for trigger in _SEARCH_TRIGGERS:

        if query.startswith(trigger):

            idx = raw_query.lower().find(trigger)

            if idx != -1:

                term = raw_query[idx + len(trigger):].strip()

            else:

                term = query[len(trigger):].strip()

            if term:

                return ToolCall("search_web", {"query": term})

    return None


def resolve_keyword_tool(query, raw_query=None):
    """Map a known command phrase to a registry ToolCall, or None.

    Deterministic, LLM-free, stdlib + registry only (importable in CI). This is
    the fast path: common voice commands resolve here without paying Ollama
    latency. A miss returns None and the caller falls back to the LLM tool
    agent. Open/close/volume/status use substring containment (so an embedded
    keyword in a longer sentence still matches); web search uses prefix
    extraction so the search term can be pulled off the trigger phrase. Checked
    in order; first match wins. "open google" beats the search triggers and the
    open_app table (it's the zero-arg homepage tool, not open_app with a name).
    `raw_query` (the un-normalized utterance) preserves case for the search term.
    """

    if raw_query is None:

        raw_query = query

    open_call = _match_named_app(query, _OPEN_APPS, "open_app")

    if open_call is not None:

        return open_call

    # "open google" routes to the zero-arg open_google homepage tool (it's kept
    # out of _OPEN_APPS, which passes a name arg, and beats the search triggers).
    if "open google" in query:

        return ToolCall("open_google", {})

    return (
        _match_named_app(query, _CLOSE_APPS, "close_app")
        or _match_substring_tool(query)
        or _match_search(query, raw_query)
    )
