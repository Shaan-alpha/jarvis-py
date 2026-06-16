import numpy as np

import core.memory.semantic_memory as sm


def _fake_encoder(calls):
    def encode(texts):
        texts = list(texts)
        calls.append(texts)
        return [np.array([float(len(t)), 1.0], dtype=np.float32) for t in texts]
    return encode


def _reset_cache():
    sm._cache["memories"] = None
    sm._cache["embeddings"] = None


def test_save_only_encodes_new_entry_once_cache_is_warm(tmp_path, monkeypatch):
    monkeypatch.setattr(sm, "MEMORY_PATH", str(tmp_path / "mem.json"))
    calls = []
    monkeypatch.setattr(sm, "encode", _fake_encoder(calls))
    _reset_cache()

    # Cache cold: these saves must not encode the stored text.
    sm.save_memory("a", "1")
    sm.save_memory("b", "2")
    assert calls == []

    # Warm the cache (one batch encoding both stored memories).
    _memories, matrix = sm._get_embeddings()
    assert matrix.shape[0] == 2

    # Now a save should encode ONLY the new entry, not all three (no O(n^2)).
    calls.clear()
    sm.save_memory("c", "3")
    assert calls == [["c 3"]]
    assert sm._cache["embeddings"].shape[0] == 3
    assert sm._cache["memories"][-1] == {"user": "c", "assistant": "3"}


def test_search_returns_a_stored_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(sm, "MEMORY_PATH", str(tmp_path / "mem.json"))
    monkeypatch.setattr(sm, "encode", _fake_encoder([]))
    _reset_cache()

    sm.save_memory("hello there", "general kenobi")
    result = sm.search_memory("hello there")

    assert result is not None
    assert set(result) == {"user", "assistant"}


def test_search_none_when_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(sm, "MEMORY_PATH", str(tmp_path / "empty.json"))
    monkeypatch.setattr(sm, "encode", _fake_encoder([]))
    _reset_cache()

    assert sm.search_memory("anything") is None
