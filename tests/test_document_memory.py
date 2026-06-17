import core.memory.document_memory as dm


class _Page:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class _Reader:
    def __init__(self, path):
        # One page returns None (scanned/empty), one returns real text.
        self.pages = [_Page(None), _Page("hello world")]


def test_read_pdf_tolerates_none_page_text(monkeypatch):
    monkeypatch.setattr(dm, "PdfReader", _Reader)
    # Must not raise even though the first page's extract_text() is None.
    text = dm.read_pdf("anything.pdf")
    assert "hello world" in text


def test_chunk_text_splits_on_size():
    chunks = dm.chunk_text("abcdef", chunk_size=2)
    assert chunks == ["ab", "cd", "ef"]
