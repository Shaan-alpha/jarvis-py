import core.ai.ollama_engine as oe


def test_ask_llm_handles_connection_error(monkeypatch):
    spoken = []

    def boom(*a, **k):
        raise oe.requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(oe.requests, "post", boom)
    monkeypatch.setattr(oe, "add_to_queue", lambda text: spoken.append(text))

    result = oe.ask_llm("hello")  # must NOT raise

    assert any("ollama" in s.lower() for s in spoken)
