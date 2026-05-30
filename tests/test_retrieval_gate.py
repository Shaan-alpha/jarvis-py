import core.ai.ollama_engine as engine


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
