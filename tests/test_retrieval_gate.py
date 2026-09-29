import json

import core.ai.ollama_engine as engine


class _StreamedReply:
    """Stand-in for a streamed Ollama 200 that yields two tokens."""

    ok = True

    status_code = 200

    def iter_lines(self):
        for token in ("hello", " there."):
            yield json.dumps({"response": token}).encode("utf-8")

    def close(self):
        pass


def _capture_payload(monkeypatch):
    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured.update(json or {})
        return _StreamedReply()

    monkeypatch.setattr(engine.requests, "post", fake_post)
    monkeypatch.setattr(engine, "add_to_queue", lambda text: None)
    monkeypatch.setattr(engine, "get_profile_context", lambda: "")

    return captured


def test_reply_generation_is_bounded(monkeypatch):
    # phi3 ignores "two sentences max" in the prompt: an unbounded generation ran
    # for minutes and invented a whole new conversation ("Instruction:", a fresh
    # "User Profile:"). Every token of that is read aloud, so the request itself
    # has to carry the ceiling.
    captured = _capture_payload(monkeypatch)

    engine.ask_llm("say hello in five words")

    options = captured.get("options", {})

    assert options.get("num_predict", 0) > 0

    # Stop at the turn markers the model invents when it starts a new dialogue.
    assert any("User:" in stop for stop in options.get("stop", []))
    assert options.get("num_ctx") == 2048
    assert captured.get("keep_alive") == "10m"


def test_chitchat_skips_retrieval():
    for phrase in ["hi", "hello", "how are you", "how are you?", "thanks", "who are you"]:
        assert engine._should_retrieve(phrase) is False, phrase


def test_short_queries_skip_retrieval():
    assert engine._should_retrieve("how") is False
    assert engine._should_retrieve("the weather") is False


def test_substantial_questions_retrieve():
    assert engine._should_retrieve("what does my resume say about ETL pipelines") is True
    assert engine._should_retrieve("summarize the document I uploaded") is True


def test_gate_is_case_and_punctuation_insensitive():
    assert engine._should_retrieve("  HELLO!! ") is False
    assert engine._should_retrieve("How Are You?") is False


def test_new_generation_supersedes_previous():
    first = engine._start_generation()
    assert engine._is_current(first) is True

    second = engine._start_generation()
    # The newer generation is current; the older one is now superseded.
    assert engine._is_current(second) is True
    assert engine._is_current(first) is False
