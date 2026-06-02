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

# Ordered: "search google for " before "google " so the longer, more specific
# trigger wins (otherwise "google " would swallow it and mis-extract the term).
_SEARCH_TRIGGERS = (
    "search google for ",
    "search the web for ",
    "search for ",
    "google ",
)


def resolve_keyword_tool(query):
    """Map a known command phrase to a registry ToolCall, or None.

    Deterministic, LLM-free, stdlib + registry only (importable in CI). This is
    the fast path: common voice commands resolve here without paying Ollama
    latency. A miss returns None and the caller falls back to the LLM tool
    agent. Open/close/volume/status use substring containment (so an embedded
    keyword in a longer sentence still matches); web search uses prefix
    extraction so the search term can be pulled off the trigger phrase.
    """

    # Open apps.
    for phrase, name in _OPEN_APPS.items():

        if phrase in query:

            return ToolCall("open_app", {"name": name})

    # "open google" routes to the zero-arg open_google tool (homepage), not
    # open_app -- so it's kept out of the _OPEN_APPS dict, which passes a
    # name arg. (It also can't collide with the prefix-based search triggers.)
    if "open google" in query:

        return ToolCall("open_google", {})

    # Close apps.
    for phrase, name in _CLOSE_APPS.items():

        if phrase in query:

            return ToolCall("close_app", {"name": name})

    # Volume.
    if any(p in query for p in _INCREASE_VOLUME):

        return ToolCall("increase_volume", {})

    if any(p in query for p in _DECREASE_VOLUME):

        return ToolCall("decrease_volume", {})

    # Substring match (preserves the legacy router's behavior): a word like
    # "commute" would also match. Acceptable for a single-user voice assistant.
    if "mute" in query:

        return ToolCall("mute_volume", {})

    # System status.
    if any(p in query for p in _SYSTEM_STATUS):

        return ToolCall("system_status", {})

    # Web search: strip the trigger prefix to get the search term.
    for trigger in _SEARCH_TRIGGERS:

        if query.startswith(trigger):

            term = query[len(trigger):].strip()

            if term:

                return ToolCall("search_web", {"query": term})

    return None
