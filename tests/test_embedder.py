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


def test_lazy_init_happens_on_first_encode(monkeypatch):
    # Exercises the actual _get_embedder() init branch: with the sentinel
    # reset to None, the first encode() must lazily construct the embedder
    # (here a fake, so no real model loads) and cache it.
    monkeypatch.setattr(emb, "_text_embedder", None)
    fake = _FakeEmbedder()
    monkeypatch.setattr("fastembed.TextEmbedding", lambda **kwargs: fake)
    emb.encode("warm up")
    assert emb._text_embedder is fake
