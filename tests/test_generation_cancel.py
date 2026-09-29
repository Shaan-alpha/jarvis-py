import json

import app
import core.ai.ollama_engine as engine


class _CancelledMidStream:
    """A streamed reply during which the user presses Stop after one sentence."""

    ok = True
    status_code = 200

    def __init__(self):
        self.closed = False

    def iter_lines(self):
        yield json.dumps({"response": "One."}).encode("utf-8")
        yield json.dumps({"response": " Two"}).encode("utf-8")
        engine.cancel_generation()
        yield json.dumps({"response": " three."}).encode("utf-8")
        yield json.dumps({"response": " Four."}).encode("utf-8")

    def close(self):
        self.closed = True


def test_cancel_generation_stops_a_streaming_answer(monkeypatch):
    stream = _CancelledMidStream()
    queued, emitted = [], []
    monkeypatch.setattr(engine.requests, "post", lambda *a, **k: stream)
    monkeypatch.setattr(engine, "add_to_queue", queued.append)
    monkeypatch.setattr(engine, "get_profile_context", lambda: "")
    monkeypatch.setattr(engine.events, "emit", lambda evt, **kw: emitted.append(evt))

    result = engine.ask_llm("say something")

    assert result == ""
    assert queued == ["One."]
    assert stream.closed is True
    assert "assistant_done" not in emitted


class _Session:
    def __init__(self, calls):
        self.calls = calls

    def activate(self):
        self.calls.append("activate")


def _record(monkeypatch, calls):
    monkeypatch.setattr(app, "cancel_generation", lambda: calls.append("cancel"))
    monkeypatch.setattr(app, "stop_speaking", lambda: calls.append("stop"))
    monkeypatch.setattr(app, "clear_queue", lambda: calls.append("clear"))


def test_stop_cancels_generation_before_silencing(monkeypatch):
    calls = []
    _record(monkeypatch, calls)
    app._hud_on_stop()
    assert calls == ["cancel", "stop", "clear"]


def test_typed_query_cancels_the_previous_answer_first(monkeypatch):
    calls = []
    _record(monkeypatch, calls)
    monkeypatch.setattr(app, "_spawn", lambda target, *a, **k: calls.append("spawn"))
    app._hud_on_text_query(_Session(calls), object(), "Open Notepad")
    assert calls == ["cancel", "stop", "clear", "activate", "spawn"]


def test_typed_query_is_normalized_but_keeps_the_raw_text(monkeypatch):
    seen = {}
    for name in ("cancel_generation", "stop_speaking", "clear_queue"):
        monkeypatch.setattr(app, name, lambda: None)
    monkeypatch.setattr(app, "_spawn", lambda target, *a, **k: seen.update(args=a, kwargs=k))
    app._hud_on_text_query(_Session([]), "tm", "What's on my Clipboard?")
    assert seen["args"] == ("whats on my clipboard", "tm")
    assert seen["kwargs"] == {"source": "text", "raw_query": "What's on my Clipboard?"}
