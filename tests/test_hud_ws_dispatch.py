import logging

import core.hud.ws_server as ws


def test_server_thread_logs_instead_of_dying_when_the_port_is_taken(
    monkeypatch, caplog
):
    # Port 8765 is already bound when a second Jarvis is started (or an earlier
    # one never exited). The bind failure used to surface as an unhandled
    # exception in a daemon thread: the app carried on, the HUD never connected,
    # and nothing explained why.
    async def _refuse():
        raise OSError("[Errno 10048] address already in use")

    monkeypatch.setattr(ws, "_serve", _refuse)

    with caplog.at_level(logging.ERROR):

        ws._run_server_loop()   # must not raise

    assert any("8765" in record.message for record in caplog.records)


class _ModernConnection:
    """websockets >= 14: the handler gets a ServerConnection with `.request`."""

    class _Request:
        headers = {"Origin": "https://evil.example"}

    request = _Request()


class _LegacyConnection:
    """websockets < 14: `websockets.serve` was the legacy implementation, whose
    protocol object carries `request_headers` and has no `.request` at all."""

    request_headers = {"Origin": "https://evil.example"}


def test_origin_is_read_from_a_modern_connection():
    assert ws._read_origin(_ModernConnection()) == "https://evil.example"


def test_unreadable_origin_is_reported_not_swallowed(caplog):
    # Silently treating an unreadable Origin as absent means _origin_allowed()
    # waves every connection through — the Origin check becomes a no-op and
    # nothing says so. Say so.
    with caplog.at_level(logging.WARNING):

        assert ws._read_origin(_LegacyConnection()) is None

    assert any("origin" in record.message.lower() for record in caplog.records)


def setup_function():
    ws._handlers.clear()
    ws.set_wizard_mode(False)


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


def _must_not_run():
    raise AssertionError("handler should not be called for an unknown type")


def test_shutdown_calls_zero_arg_handler():
    calls = []
    ws.register_handlers(shutdown=lambda: calls.append("shutdown"))
    ws._dispatch_command('{"type": "shutdown"}')
    assert calls == ["shutdown"]


def test_unknown_type_is_ignored():
    ws.register_handlers(stop=_must_not_run)
    assert ws._dispatch_command('{"type": "foo"}') is None


def test_bad_json_is_ignored():
    assert ws._dispatch_command("not json") is None


def test_origin_allows_file_and_null_and_absent():
    assert ws._origin_allowed(None) is True
    assert ws._origin_allowed("") is True
    assert ws._origin_allowed("null") is True
    assert ws._origin_allowed("file:///C:/x/index.html") is True


def test_origin_rejects_web_pages():
    assert ws._origin_allowed("http://evil.example") is False
    assert ws._origin_allowed("https://evil.example") is False
    assert ws._origin_allowed("HTTPS://Evil.Example") is False


def test_wizard_mode_defaults_false():
    assert ws._wizard_mode is False


def test_set_wizard_mode_toggles_flag():
    ws.set_wizard_mode(True)
    assert ws._wizard_mode is True
    ws.set_wizard_mode(0)
    assert ws._wizard_mode is False
