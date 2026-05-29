import core.memory.embedder as emb


class _FakeEmbedder:
    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_encode_wraps_string_and_uses_embedder(monkeypatch):
    fake = _FakeEmbedder()
    monkeypatch.setattr(emb, "_text_embedder", fake)
    out = emb.encode("hello")
    assert fake.calls == [["hello"]]
    assert len(out) == 1


def test_encode_passes_list_through(monkeypatch):
    fake = _FakeEmbedder()
    monkeypatch.setattr(emb, "_text_embedder", fake)
    out = emb.encode(["a", "b"])
    assert fake.calls == [["a", "b"]]
    assert len(out) == 2
