import core.ai.ollama_engine as oe
import core.speech.engine as se
import core.speech.offline_recognizer as off


def test_ask_llm_handles_connection_error(monkeypatch):
    spoken = []

    def boom(*a, **k):
        raise oe.requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(oe.requests, "post", boom)
    monkeypatch.setattr(oe, "add_to_queue", lambda text: spoken.append(text))

    result = oe.ask_llm("hello")  # must NOT raise

    assert any("ollama" in s.lower() for s in spoken)


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


def test_offline_returns_none_when_model_load_fails(monkeypatch):
    def boom():
        raise RuntimeError("vosk model missing")

    monkeypatch.setattr(off, "_get_model", boom)
    result = off.recognize_offline(recognizer=None, audio=None)
    assert result == "none"
