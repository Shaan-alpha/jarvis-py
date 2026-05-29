from core.agent.tool_agent import (
    _extract_first_json,
    _looks_like_action,
)
from core.agent.tool_registry import TOOLS


def test_action_verb_at_start_passes_gate():
    assert _looks_like_action("open the calculator") is True
    assert _looks_like_action("increase the volume please") is True


def test_question_does_not_look_like_action():
    assert _looks_like_action("what is python") is False
    assert _looks_like_action("explain transformers in two lines") is False


def test_extracts_clean_json_object():
    assert _extract_first_json('{"tool": "open_calculator"}') == {
        "tool": "open_calculator"
    }


def test_extracts_json_from_markdown_fence():
    text = '```json\n{"tool": "mute_volume"}\n```'
    assert _extract_first_json(text) == {"tool": "mute_volume"}


def test_extracts_json_surrounded_by_prose():
    text = 'Sure! Here you go: {"tool": "open_google"} hope that helps'
    assert _extract_first_json(text) == {"tool": "open_google"}


def test_returns_none_for_unparseable_text():
    assert _extract_first_json("no json here at all") is None


def test_registered_tools_present():
    # Guards against accidental registry edits breaking the executor.
    for tool in ("open_calculator", "increase_volume", "mute_volume"):
        assert tool in TOOLS
