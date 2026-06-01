from core.agent import tool_executor
from core.agent import registry


def test_dispatches_with_args():
    captured = {}

    @registry.tool("echo", "echo",
                   params={"msg": {"type": "str", "required": True}})
    def _echo(msg):
        captured["msg"] = msg
        return f"said {msg}"

    out = tool_executor.execute_tool(registry.ToolCall("echo", {"msg": "hi"}))
    assert out == "said hi"
    assert captured["msg"] == "hi"


def test_unknown_tool_returns_none():
    assert tool_executor.execute_tool(registry.ToolCall("nope", {})) is None


def test_handler_error_returns_message():
    @registry.tool("boom", "boom")
    def _boom():
        raise RuntimeError("kaboom")

    out = tool_executor.execute_tool(registry.ToolCall("boom", {}))
    assert out == "Tool execution failed."
