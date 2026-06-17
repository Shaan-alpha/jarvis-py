from core.agent import registry
from core.agent.registry import ParamSpec, ToolSpec, coerce_and_validate


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


def _spec(params):
    return ToolSpec("t", "d", params, lambda **k: None)


def test_coerce_int_and_str():
    spec = _spec({"n": ParamSpec(type="int"), "s": ParamSpec(type="str")})
    args, err = coerce_and_validate(spec, {"n": "5", "s": 7})
    assert err is None
    assert args == {"n": 5, "s": "7"}


def test_default_filled_for_missing_optional():
    spec = _spec({"sides": ParamSpec(type="int", required=False, default=6)})
    args, err = coerce_and_validate(spec, {})
    assert err is None
    assert args == {"sides": 6}


def test_missing_required_is_error():
    spec = _spec({"name": ParamSpec(type="str", required=True)})
    args, err = coerce_and_validate(spec, {})
    assert err is not None
    assert "name" in err


def test_uncoercible_is_error():
    spec = _spec({"n": ParamSpec(type="int", required=True)})
    args, err = coerce_and_validate(spec, {"n": "not-a-number"})
    assert err is not None


def test_unknown_keys_dropped():
    spec = _spec({"n": ParamSpec(type="int", required=False, default=0)})
    args, err = coerce_and_validate(spec, {"n": 1, "bogus": "x"})
    assert err is None
    assert args == {"n": 1}


def test_none_raw_args_treated_as_empty():
    spec = _spec({"sides": ParamSpec(type="int", required=False, default=6)})
    args, err = coerce_and_validate(spec, None)
    assert err is None
    assert args == {"sides": 6}


def test_null_optional_uses_default():
    spec = _spec({"sides": ParamSpec(type="int", required=False, default=6)})
    args, err = coerce_and_validate(spec, {"sides": None})
    assert err is None
    assert args == {"sides": 6}


def test_coerce_float():
    spec = _spec({"x": ParamSpec(type="float")})
    args, err = coerce_and_validate(spec, {"x": "3.5"})
    assert err is None
    assert args == {"x": 3.5}


def test_coerce_bool_from_strings():
    spec = _spec({"b": ParamSpec(type="bool")})
    for raw, expected in (("true", True), ("false", False),
                          ("yes", True), ("0", False), (True, True)):
        args, err = coerce_and_validate(spec, {"b": raw})
        assert err is None
        assert args == {"b": expected}


def test_coerce_bool_rejects_garbage():
    spec = _spec({"b": ParamSpec(type="bool", required=True)})
    args, err = coerce_and_validate(spec, {"b": "maybe"})
    assert err is not None
