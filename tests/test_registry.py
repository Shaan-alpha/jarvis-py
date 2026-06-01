from core.agent import registry


def test_tool_decorator_registers():
    registry.clear()

    @registry.tool("ping", "say pong")
    def _ping():
        return "pong"

    spec = registry.get("ping")
    assert spec is not None
    assert spec.name == "ping"
    assert spec.description == "say pong"
    assert spec.params == {}
    assert spec.handler() == "pong"


def test_tool_decorator_builds_param_specs():
    registry.clear()

    @registry.tool("greet", "greet someone",
                   params={"who": {"type": "str", "required": True, "desc": "name"}})
    def _greet(who):
        return f"hi {who}"

    spec = registry.get("greet")
    assert set(spec.params) == {"who"}
    assert spec.params["who"].type == "str"
    assert spec.params["who"].required is True
    assert spec.params["who"].desc == "name"


def test_all_tools_and_clear():
    registry.clear()

    @registry.tool("a", "tool a")
    def _a():
        return None

    @registry.tool("b", "tool b")
    def _b():
        return None

    assert {s.name for s in registry.all_tools()} == {"a", "b"}
    registry.clear()
    assert registry.all_tools() == []


def test_duplicate_name_last_wins():
    registry.clear()

    @registry.tool("dup", "first")
    def _first():
        return "first"

    @registry.tool("dup", "second")
    def _second():
        return "second"

    assert registry.get("dup").handler() == "second"
