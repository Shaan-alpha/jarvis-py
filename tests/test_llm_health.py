import core.ai.llm_health as health
import core.ai.ollama_engine as engine
from core.agent import tool_agent


def test_down_state_expires():
    health.mark_down("connection refused", now=100.0)
    assert health.is_down(now=110.0) is True
    assert health.is_down(now=100.0 + health.LLM_DOWN_SECONDS + 1) is False


def test_mark_up_clears_it():
    health.mark_down("x", now=100.0)
    health.mark_up()
    assert health.is_down(now=101.0) is False


def test_message_blames_memory_when_that_was_the_cause():
    health.mark_down("model requires more system memory (5.0 GiB) than is available")
    assert "memory" in health.unavailable_message().lower()


def test_message_says_what_still_works():
    health.mark_down("connection refused")
    message = health.unavailable_message()
    assert "time" in message and "files" in message


def _no_http(*a, **k):
    raise AssertionError("must not call Ollama while it is marked down")


def test_ask_llm_answers_at_once_while_the_model_is_down(monkeypatch):
    health.mark_down("connection refused")
    spoken = []
    monkeypatch.setattr(engine.requests, "post", _no_http)
    monkeypatch.setattr(engine, "add_to_queue", spoken.append)
    assert engine.ask_llm("hello there") == ""
    assert spoken and "language model" in spoken[0]


def test_a_connection_error_marks_the_model_down(monkeypatch):
    def boom(*a, **k):
        raise engine.requests.exceptions.ConnectionError("refused")
    monkeypatch.setattr(engine.requests, "post", boom)
    monkeypatch.setattr(engine, "add_to_queue", lambda t: None)
    engine.ask_llm("hello")
    assert health.is_down() is True


def test_decide_tool_skips_while_the_model_is_down(monkeypatch):
    health.mark_down("connection refused")
    monkeypatch.setattr(tool_agent.requests, "post", _no_http)
    assert tool_agent.decide_tool("open spotify") is None
