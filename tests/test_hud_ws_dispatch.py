import core.hud.ws_server as ws


def setup_function():
    ws._handlers.clear()


def test_text_query_calls_handler_with_text():
    got = {}
    ws.register_handlers(text_query=lambda text: got.setdefault("t", text))
    ws._dispatch_command('{"type": "text_query", "text": "hello"}')
    assert got["t"] == "hello"


def test_wake_calls_zero_arg_handler():
    calls = []
    ws.register_handlers(wake=lambda: calls.append("wake"))
    ws._dispatch_command('{"type": "wake"}')
    assert calls == ["wake"]


def test_unknown_type_is_ignored():
    ws.register_handlers(stop=lambda: (_ for _ in ()).throw(AssertionError("should not run")))
    assert ws._dispatch_command('{"type": "foo"}') is None


def test_bad_json_is_ignored():
    assert ws._dispatch_command("not json") is None
