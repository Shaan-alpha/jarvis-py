import json
from datetime import datetime

import core.ai.ollama_engine as engine


class _Stream:
    ok = True
    status_code = 200

    def __init__(self, tokens):
        self.tokens = tokens
        self.closed = False

    def iter_lines(self):
        for token in self.tokens:
            yield json.dumps({"response": token}).encode("utf-8")

    def close(self):
        self.closed = True


def _serve(monkeypatch, tokens):
    stream, queued, captured = _Stream(tokens), [], {}

    def fake_post(url, json=None, **kwargs):
        captured.update(json or {})
        return stream

    monkeypatch.setattr(engine.requests, "post", fake_post)
    monkeypatch.setattr(engine, "add_to_queue", queued.append)
    monkeypatch.setattr(engine, "get_profile_context", lambda: "")
    return stream, queued, captured


def test_prompt_is_grounded_in_the_clock_and_rules():
    prompt = engine.build_prompt("what is the capital of peru",
                                 now=datetime(2026, 9, 28, 16, 5), online=False)
    assert "Monday, 28 September 2026, 4:05 PM" in prompt
    assert "Internet: offline" in prompt
    assert "don't know" in prompt
    assert "Never claim" in prompt
    assert "two short sentences" in prompt
    assert prompt.rstrip().endswith("User: what is the capital of peru\nJarvis:")


def test_prompt_carries_recent_conversation():
    prompt = engine.build_prompt("how tall is he", now=datetime(2026, 9, 28, 16, 5), online=True,
                                 history=[("who is sachin tendulkar", "An Indian cricketer.")])
    assert "Recent conversation" in prompt
    assert "who is sachin tendulkar" in prompt


def test_reply_is_cut_after_two_sentences(monkeypatch):
    stream, queued, _ = _serve(monkeypatch, ["First one.", " Second one.", " Third one.", " Fourth."])
    assert engine.ask_llm("say something") == "First one. Second one."
    assert queued == ["First one.", "Second one."]
    assert stream.closed is True


def test_a_decimal_point_does_not_split_a_sentence(monkeypatch):
    _, queued, _ = _serve(monkeypatch, ["Pi is about 3.", "14 today."])
    engine.ask_llm("say something")
    assert queued == ["Pi is about 3.14 today."]


def test_detailed_mode_allows_a_longer_answer(monkeypatch):
    _, queued, captured = _serve(monkeypatch, ["One.", " Two.", " Three.", " Four."])
    engine.ask_llm("say something", detailed=True)
    assert queued == ["One.", "Two.", "Three.", "Four."]
    assert captured["options"]["num_predict"] == engine.DETAILED_TOKEN_LIMIT


def test_request_is_low_temperature_and_short(monkeypatch):
    _, _, captured = _serve(monkeypatch, ["Hi."])
    engine.ask_llm("say something")
    options = captured["options"]
    assert options["temperature"] == 0.2
    assert options["num_predict"] == engine.REPLY_TOKEN_LIMIT <= 100
    assert "\nRules:" in options["stop"]


def test_only_relevant_remembered_facts_reach_the_prompt(monkeypatch):
    _, _, captured = _serve(monkeypatch, ["Friday."])
    monkeypatch.setattr(engine, "search_facts", lambda q, k=3: ["my exam is on the fifth"])
    monkeypatch.setattr(engine, "search_chunks", lambda q: [])
    engine.ask_llm("when is my exam happening")
    assert "my exam is on the fifth" in captured["prompt"]
    assert "Relevant Memory" not in captured["prompt"]


def test_document_snippets_name_their_file(monkeypatch):
    _, _, captured = _serve(monkeypatch, ["Yes."])
    monkeypatch.setattr(engine, "search_facts", lambda q, k=3: [])
    monkeypatch.setattr(engine, "search_chunks",
                        lambda q: [{"file": "resume.pdf", "text": "Built ETL pipelines.", "score": 0.9}])
    engine.ask_llm("what does my resume say about pipelines")
    assert "[resume.pdf] Built ETL pipelines." in captured["prompt"]
