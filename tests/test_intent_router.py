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
    ("raise volume", ToolCall("increase_volume", {})),
    ("volume down", ToolCall("decrease_volume", {})),
    ("decrease the volume", ToolCall("decrease_volume", {})),
    ("decrease volume", ToolCall("decrease_volume", {})),
    ("lower volume", ToolCall("decrease_volume", {})),
    ("lower the volume", ToolCall("decrease_volume", {})),
    ("mute", ToolCall("mute_volume", {})),
    ("volume mute", ToolCall("mute_volume", {})),
    ("system status", ToolCall("system_status", {})),
    ("system info", ToolCall("system_status", {})),
    ("cpu usage", ToolCall("system_status", {})),
    ("battery level", ToolCall("battery_status", {})),
    ("battery percentage", ToolCall("battery_status", {})),
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


@pytest.mark.parametrize("query", [
    "read clipboard",
    "read my clipboard",
    "what's on my clipboard",
    "what's in my clipboard",
    "what's on the clipboard",
    "check clipboard",
    "show clipboard",
])
def test_clipboard_read_phrases_route(query):
    assert resolve_keyword_tool(query) == ToolCall("read_clipboard", {})


def test_clipboard_read_substring_in_sentence():
    assert resolve_keyword_tool("hey jarvis what's on my clipboard please") == \
        ToolCall("read_clipboard", {})


def test_copy_command_is_not_a_clipboard_read():
    # "copy ... to clipboard" must fall through to the LLM (write_clipboard),
    # not match a read phrase.
    assert resolve_keyword_tool("copy hello to clipboard") is None


_LIST_FILES_PHRASES = [
    "list files",
    "list my files",
    "what files do i have",
    "what's in my workspace",
    "show my files",
    "show my workspace",
]


@pytest.mark.parametrize("phrase", _LIST_FILES_PHRASES)
def test_list_files_keyword_path(phrase):
    call = resolve_keyword_tool(phrase)
    assert call is not None
    assert call.name == "list_files"
    assert call.args == {}


def test_list_files_substring_in_sentence():
    call = resolve_keyword_tool("hey jarvis list my files please")
    assert call is not None
    assert call.name == "list_files"


def test_read_file_falls_through_to_llm():
    # Arg-bearing fs tools are LLM-only; the keyword resolver must miss.
    assert resolve_keyword_tool("read notes.txt") is None


def test_search_preserves_case_from_raw_query():
    raw = "search for Tony Stark"
    call = resolve_keyword_tool(raw.lower(), raw_query=raw)
    assert call == ToolCall("search_web", {"query": "Tony Stark"})


def test_search_without_raw_query_uses_normalized():
    # Backward compatible: no raw_query -> term comes from the (lowercased) query.
    assert resolve_keyword_tool("search for cats") == \
        ToolCall("search_web", {"query": "cats"})


def test_typed_apostrophes_match_like_voice():
    assert resolve_keyword_tool("What's on my clipboard?") == ToolCall("read_clipboard", {})


def test_mute_needs_a_whole_word():
    assert resolve_keyword_tool("i commute by bus") is None
    assert resolve_keyword_tool("please mute") == ToolCall("mute_volume", {})


@pytest.mark.parametrize("query,tool", [
    ("what time is it", "get_time"),
    ("whats the time", "get_time"),
    ("What's the time?", "get_time"),
    ("hey jarvis what time is it please", "get_time"),
    ("tell me the time", "get_time"),
    ("what is todays date", "get_date"),
    ("whats the date today", "get_date"),
    ("what day is it", "get_day"),
    ("which day is today", "get_day"),
    ("battery", "battery_status"),
    ("whats my battery", "battery_status"),
    ("how much battery is left", "battery_status"),
    ("battery level", "battery_status"),
    ("battery percentage", "battery_status"),
    ("is my laptop charging", "battery_status"),
    ("how much ram am i using", "memory_usage"),
    ("memory usage", "memory_usage"),
    ("how much disk space do i have", "disk_space"),
    ("free space", "disk_space"),
    ("uptime", "uptime"),
    ("how long has my pc been on", "uptime"),
    ("am i online", "network_status"),
    ("is the internet working", "network_status"),
])
def test_info_questions_route_to_deterministic_tools(query, tool):
    assert resolve_keyword_tool(query) == ToolCall(tool, {})


@pytest.mark.parametrize("query", [
    "what is the time complexity of quicksort",
    "what time is it in london",
    "last time i checked it was fine",
    "what day is christmas",
    "my phone battery died",
    "what do you remember",
])
def test_ordinary_sentences_do_not_hit_info_tools(query):
    call = resolve_keyword_tool(query)
    assert call is None or call.name not in {
        "get_time", "get_date", "get_day", "battery_status",
        "memory_usage", "disk_space", "uptime", "network_status"}


def test_maths_routes_to_the_calculator():
    assert resolve_keyword_tool("whats 25 times 17", raw_query="What's 25 times 17?") == \
        ToolCall("calculate", {"expression": "25 * 17"})
    assert resolve_keyword_tool("twenty five times seventeen") == \
        ToolCall("calculate", {"expression": "25 * 17"})


def test_what_is_a_word_is_not_maths():
    call = resolve_keyword_tool("what is python")
    assert call is None or call.name != "calculate"
