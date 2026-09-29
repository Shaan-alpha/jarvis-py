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


import os

import numpy as np


def _setup(monkeypatch, tmp_path):
    docs = tmp_path / "documents"
    docs.mkdir()
    monkeypatch.setattr(dm, "DOCS_PATH", str(docs))
    monkeypatch.setattr(dm, "INDEX_PATH", str(tmp_path / "vector.index"))
    monkeypatch.setattr(dm, "CHUNKS_PATH", str(tmp_path / "chunks.json"))
    monkeypatch.setattr(dm, "MANIFEST_PATH", str(tmp_path / "manifest.json"))
    monkeypatch.setattr(dm, "read_pdf", lambda path: "invoice total due")
    monkeypatch.setattr(dm, "encode",
                        lambda texts: [np.array([1.0, 0.0], dtype=np.float32) for _ in texts])
    dm._invalidate_cache()
    return docs


def test_index_is_searchable_and_cites_its_file(monkeypatch, tmp_path):
    docs = _setup(monkeypatch, tmp_path)
    (docs / "bill.pdf").write_bytes(b"%PDF")
    assert dm.build_index() == (1, 1)
    assert dm.index_state() == "ready"
    assert dm.search_chunks("invoice")[0]["file"] == "bill.pdf"
    assert dm.search_documents("invoice") == ["invoice total due"]


def test_a_deleted_document_is_never_served(monkeypatch, tmp_path):
    docs = _setup(monkeypatch, tmp_path)
    pdf = docs / "bill.pdf"
    pdf.write_bytes(b"%PDF")
    dm.build_index()
    assert dm.search_documents("invoice")
    pdf.unlink()
    assert dm.index_state() == "stale"
    assert dm.search_documents("invoice") == []


def test_legacy_index_without_manifest_is_ignored(monkeypatch, tmp_path):
    docs = _setup(monkeypatch, tmp_path)
    (docs / "bill.pdf").write_bytes(b"%PDF")
    dm.build_index()
    os.remove(dm.MANIFEST_PATH)
    dm._invalidate_cache()
    assert dm.search_documents("invoice") == []


def test_rebuilding_with_no_pdfs_clears_the_old_index(monkeypatch, tmp_path):
    docs = _setup(monkeypatch, tmp_path)
    pdf = docs / "bill.pdf"
    pdf.write_bytes(b"%PDF")
    dm.build_index()
    pdf.unlink()
    assert dm.build_index() == (0, 0)
    assert not os.path.exists(dm.INDEX_PATH)
    assert dm.index_state() == "missing"
