import core.hud.ws_server as ws


def setup_function():
    ws._handlers.clear()


def test_save_name_receives_name():
    got = {}
    ws.register_handlers(save_name=lambda name: got.setdefault("n", name))
    ws._dispatch_command('{"type": "save_name", "name": "Shaan"}')
    assert got["n"] == "Shaan"


def test_pull_model_receives_model():
    got = {}
    ws.register_handlers(pull_model=lambda model: got.setdefault("m", model))
    ws._dispatch_command('{"type": "pull_model", "model": "phi3"}')
    assert got["m"] == "phi3"


def test_run_checks_is_zero_arg():
    calls = []
    ws.register_handlers(run_checks=lambda: calls.append("ran"))
    ws._dispatch_command('{"type": "run_checks"}')
    assert calls == ["ran"]
