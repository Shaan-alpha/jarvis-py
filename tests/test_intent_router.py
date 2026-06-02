import pytest

from core.router.intent_router import resolve_keyword_tool
from core.agent.registry import ToolCall


@pytest.mark.parametrize("query,expected", [
    ("open calculator", ToolCall("open_app", {"name": "calculator"})),
    ("open notepad", ToolCall("open_app", {"name": "notepad"})),
    ("open paint", ToolCall("open_app", {"name": "paint"})),
    ("open edge", ToolCall("open_app", {"name": "edge"})),
    ("open google", ToolCall("open_google", {})),
    ("close calculator", ToolCall("close_app", {"name": "calculator"})),
    ("close notepad", ToolCall("close_app", {"name": "notepad"})),
    ("close paint", ToolCall("close_app", {"name": "paint"})),
    ("volume up", ToolCall("increase_volume", {})),
    ("increase volume", ToolCall("increase_volume", {})),
    ("increase the volume", ToolCall("increase_volume", {})),
    ("raise the volume", ToolCall("increase_volume", {})),
    ("volume down", ToolCall("decrease_volume", {})),
    ("decrease the volume", ToolCall("decrease_volume", {})),
    ("lower volume", ToolCall("decrease_volume", {})),
    ("mute", ToolCall("mute_volume", {})),
    ("volume mute", ToolCall("mute_volume", {})),
    ("system status", ToolCall("system_status", {})),
    ("system info", ToolCall("system_status", {})),
    ("cpu usage", ToolCall("system_status", {})),
    ("battery level", ToolCall("system_status", {})),
    ("battery percentage", ToolCall("system_status", {})),
    ("search google for cats", ToolCall("search_web", {"query": "cats"})),
    ("search the web for cats", ToolCall("search_web", {"query": "cats"})),
    ("search for cats", ToolCall("search_web", {"query": "cats"})),
    ("google cats", ToolCall("search_web", {"query": "cats"})),
])
def test_resolve_returns_expected_toolcall(query, expected):
    assert resolve_keyword_tool(query) == expected


def test_substring_match_inside_a_sentence_still_routes():
    # Substring containment is preserved for the open/close/volume commands.
    assert resolve_keyword_tool("hey can you open notepad for me") == \
        ToolCall("open_app", {"name": "notepad"})


def test_open_google_is_homepage_not_search():
    # "open google" must beat the search triggers -> homepage, not a web search.
    assert resolve_keyword_tool("open google") == ToolCall("open_google", {})


def test_bare_google_with_no_term_is_not_a_search():
    # "google" with nothing after it is not a command; fall through to the LLM.
    assert resolve_keyword_tool("google") is None


def test_unmatched_query_returns_none():
    # Falls through to the LLM tool agent / chat in the real pipeline.
    for query in ("what is python", "tell me a joke", "open spotify"):
        assert resolve_keyword_tool(query) is None
