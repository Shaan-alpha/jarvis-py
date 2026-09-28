from pathlib import Path

import pytest

import core.agent.search_tools as st
from core.state.conversation import conversation


@pytest.fixture
def sources(monkeypatch):
    found = {"files": [], "chunks": [], "facts": []}
    monkeypatch.setattr(st, "user_roots", lambda: {"downloads": Path("/u/Downloads")})
    monkeypatch.setattr(st, "find_paths", lambda q, roots=None: found["files"])
    monkeypatch.setattr(st, "search_chunks", lambda q, top_k=2: found["chunks"])
    monkeypatch.setattr(st, "search_facts", lambda q, k=2: found["facts"])
    monkeypatch.setattr(st, "index_state", lambda: "ready")
    return found


def test_search_local_combines_files_documents_and_memory(sources):
    sources["files"] = [Path("/u/Downloads/tax 2025.pdf")]
    sources["chunks"] = [{"file": "salary.pdf", "text": "tax deducted at source", "score": 0.8}]
    sources["facts"] = ["my tax id is abc"]
    out = st.search_local("tax")
    assert out.say == "I found 1 file, like tax 2025.pdf, a match in salary.pdf, and something you asked me to remember."
    assert "Files:" in out.show and "salary.pdf" in out.show
    assert conversation.results() == [str(Path("/u/Downloads/tax 2025.pdf"))]


def test_search_local_nothing_suggests_the_web(sources):
    assert st.search_local("unicorns") == \
        "Nothing local for unicorns. Say 'search the web for unicorns' to look online."


def test_document_search_cites_the_file(sources):
    sources["chunks"] = [{"file": "resume.pdf", "text": " ".join(["word"] * 40), "score": 0.9}]
    out = st.search_my_documents("skills")
    assert out.say.startswith("In resume.pdf: word word")
    assert out.say.endswith("…")


def test_document_search_when_not_indexed(sources, monkeypatch):
    monkeypatch.setattr(st, "index_state", lambda: "missing")
    assert st.search_my_documents("x") == "Your documents aren't indexed yet. Say 'index my documents'."
    monkeypatch.setattr(st, "index_state", lambda: "stale")
    assert "changed" in st.search_my_documents("x")


def test_index_documents_reports_counts(monkeypatch):
    monkeypatch.setattr(st, "build_index", lambda: (2, 40))
    assert st.index_documents() == "Indexed 2 documents."
    monkeypatch.setattr(st, "build_index", lambda: (0, 0))
    assert st.index_documents().say == "I didn't find any PDFs to index."
