from core.agent import tool_agent
from core.agent import registry


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _register_open_app():
    @registry.tool("open_app", "Open an app",
                   params={"name": {"type": "str", "required": True}})
    def _open(name):
        return f"Opening {name}."


def test_gate_passes_builtin_verb():
    assert tool_agent._looks_like_action("open notepad") is True


def test_gate_passes_tool_name_token():
    registry.clear()

    @registry.tool("roll_dice", "Roll a die")
    def _r():
        return "rolled"

    assert tool_agent._looks_like_action("roll a dice") is True


def test_gate_blocks_chitchat():
    registry.clear()
    assert tool_agent._looks_like_action("what is python") is False


def test_gate_ignores_tool_token_in_long_sentence():
    registry.clear()

    @registry.tool("roll_dice", "Roll a die")
    def _r():
        return "rolled"

    # Contains the tool token "roll" but is a long conversational sentence, so
    # the bare-token fallback should NOT trip the LLM selector.
    long_chat = "i really enjoy board games and i roll a dice almost every weekend"
    assert tool_agent._looks_like_action(long_chat) is False


def test_decide_tool_parameterized(monkeypatch):
    _register_open_app()
    monkeypatch.setattr(
        tool_agent.requests, "post",
        lambda *a, **k: _Resp({"response": '{"tool": "open_app", "args": {"name": "notepad"}}'}),
    )
    call = tool_agent.decide_tool("open notepad")
    assert call == registry.ToolCall("open_app", {"name": "notepad"})


def test_decide_tool_question_is_gated_to_none():
    registry.clear()
    assert tool_agent.decide_tool("what is python") is None


def test_decide_tool_unknown_tool_is_none(monkeypatch):
    registry.clear()
    _register_open_app()
    monkeypatch.setattr(
        tool_agent.requests, "post",
        lambda *a, **k: _Resp({"response": '{"tool": "fly_to_moon", "args": {}}'}),
    )
    assert tool_agent.decide_tool("open notepad") is None


def test_decide_tool_missing_required_arg_is_none(monkeypatch):
    registry.clear()
    _register_open_app()
    monkeypatch.setattr(
        tool_agent.requests, "post",
        lambda *a, **k: _Resp({"response": '{"tool": "open_app", "args": {}}'}),
    )
    assert tool_agent.decide_tool("open something") is None


def test_extract_first_json_handles_nested():
    obj = tool_agent._extract_first_json('noise {"tool": "x", "args": {"a": 1}} trailing')
    assert obj == {"tool": "x", "args": {"a": 1}}


def test_decide_tool_caps_generation(monkeypatch):
    _register_open_app()
    captured = {}

    def _post(*a, **k):
        captured["json"] = k.get("json")
        return _Resp({"response": '{"tool": "open_app", "args": {"name": "notepad"}}'})

    monkeypatch.setattr(tool_agent.requests, "post", _post)
    tool_agent.decide_tool("open notepad")

    opts = captured["json"]["options"]
    assert opts["num_predict"] <= 100      # bounded so selection returns fast
    assert opts["temperature"] == 0        # deterministic JSON
