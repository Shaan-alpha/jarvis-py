import json

import core.ai.ollama_engine as oe
import core.speech.engine as se
import core.speech.offline_recognizer as off


def test_ask_llm_handles_connection_error(monkeypatch):
    spoken = []

    def boom(*a, **k):
        raise oe.requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(oe.requests, "post", boom)
    monkeypatch.setattr(oe, "add_to_queue", lambda text: spoken.append(text))

    oe.ask_llm("hello")  # must NOT raise

    assert any("ollama" in s.lower() for s in spoken)


class _ErrorResponse:
    """Stand-in for a requests Response carrying an error status.

    Faithful to a real streamed Ollama 500: iter_lines() yields the error JSON
    body (no "response" tokens), so without a status guard _stream_response just
    returns "" and the user hears nothing — the bug under test.
    """

    def __init__(self, status_code, error):
        self.status_code = status_code
        self.ok = status_code < 400
        self._error = error
        self.text = error

    def json(self):
        return {"error": self._error}

    def iter_lines(self):
        yield json.dumps({"error": self._error}).encode("utf-8")

    def close(self):
        pass


def test_ask_llm_speaks_on_error_status(monkeypatch):
    # Ollama can answer with a non-200 (e.g. 500 when the model needs more memory
    # than is free). The streamed body has no tokens, so without a status guard
    # the user just hears silence. ask_llm must surface something spoken instead.
    spoken = []

    def error_post(*a, **k):
        return _ErrorResponse(
            500, "model requires more system memory than is available"
        )

    monkeypatch.setattr(oe.requests, "post", error_post)
    monkeypatch.setattr(oe, "add_to_queue", lambda text: spoken.append(text))

    result = oe.ask_llm("what is the capital of france")  # must NOT raise

    assert result == ""
    assert spoken, "expected a spoken message on an Ollama error status"
    # The OOM case mentions memory so the user knows why.
    assert any("memory" in s.lower() for s in spoken)


def test_speak_sync_creates_fresh_engine_per_call(monkeypatch):
    # A pyttsx3/SAPI engine reused across runAndWait() calls only speaks the
    # first time and is silent after, so each utterance must get a fresh engine.
    calls = {"n": 0}
    said = []

    class _Eng:
        def say(self, t):
            said.append(t)

        def runAndWait(self):
            pass

        def stop(self):
            pass

    def factory():
        calls["n"] += 1
        return _Eng()

    monkeypatch.setattr(se, "create_engine", factory)

    se.speak_sync("one")
    se.speak_sync("two")
    se.speak_sync("three")

    assert calls["n"] == 3                        # fresh engine per utterance
    assert said == ["one", "two", "three"]


def test_speak_sync_survives_engine_failure(monkeypatch):
    calls = {"n": 0}
    said = []

    def flaky_engine():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("SAPI hiccup")

        class _Eng:
            def say(self, t):
                said.append(t)

            def runAndWait(self):
                pass

            def stop(self):
                pass

        return _Eng()

    monkeypatch.setattr(se, "create_engine", flaky_engine)

    se.speak_sync("hello")  # first call hits failure, must not raise
    se.speak_sync("world")  # second call recreates engine, succeeds

    assert calls["n"] == 2
    assert said == ["world"]   # second call re-inited and actually spoke
    assert se.current_engine is None


def test_speak_routes_through_locked_speak_sync(monkeypatch):
    # speak() must dispatch via speak_sync (which holds speech_lock) rather than
    # run an unlocked engine that could collide with the TTS-queue worker.
    got = []
    monkeypatch.setattr(se, "stop_speaking", lambda: None)
    monkeypatch.setattr(se, "speak_sync", lambda t: got.append(t))

    se.speak("hello there")

    if se.speech_thread:
        se.speech_thread.join(timeout=2)

    assert got == ["hello there"]


def test_offline_returns_none_when_model_load_fails(monkeypatch):
    def boom():
        raise RuntimeError("vosk model missing")

    monkeypatch.setattr(off, "_get_model", boom)
    result = off.recognize_offline(recognizer=None, audio=None)
    assert result == "none"
