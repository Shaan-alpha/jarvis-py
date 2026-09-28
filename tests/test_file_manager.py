import os

import pytest

from core.agent import fs_tools
from core.agent.registry import Reply
from core.state.conversation import conversation


@pytest.fixture
def roots(monkeypatch, tmp_path):
    folders = {name: tmp_path / name.capitalize() for name in ("downloads", "documents", "workspace")}
    for folder in folders.values():
        folder.mkdir()
    monkeypatch.setattr(fs_tools, "user_roots", lambda: folders)
    return folders


@pytest.fixture
def opened(monkeypatch):
    calls = []
    monkeypatch.setattr(fs_tools, "_startfile", calls.append)
    return calls


def test_find_file_says_where_it_is_and_remembers_it(roots):
    (roots["downloads"] / "report.pdf").write_text("x")
    out = fs_tools.find_file("report")
    assert out.say == "Found report.pdf in Downloads. Say 'open it' to open it."
    assert conversation.results() == [str(roots["downloads"] / "report.pdf")]


def test_find_file_walks_subfolders_but_skips_junk(roots):
    (roots["documents"] / "work" / "q3").mkdir(parents=True)
    (roots["documents"] / "work" / "q3" / "budget.xlsx").write_text("x")
    (roots["documents"] / "node_modules").mkdir()
    (roots["documents"] / "node_modules" / "budget.xlsx").write_text("x")
    out = fs_tools.find_file("budget")
    assert out.say.startswith("Found budget.xlsx in Documents")
    assert len(conversation.results()) == 1


def test_find_file_tolerates_a_misspelling(roots):
    (roots["downloads"] / "invoice.pdf").write_text("x")
    assert "invoice.pdf" in fs_tools.find_file("invoce").say


def test_find_file_understands_a_spoken_extension(roots):
    (roots["downloads"] / "report.pdf").write_text("x")
    assert "report.pdf" in fs_tools.find_file("report dot pdf").say


def test_find_file_nothing(roots):
    assert fs_tools.find_file("dragons") == "I couldn't find dragons."


def test_open_it_opens_the_last_result(roots, opened):
    path = roots["downloads"] / "report.pdf"
    path.write_text("x")
    fs_tools.find_file("report")
    assert fs_tools.open_file("it") == "Opening report.pdf."
    assert opened == [str(path)]


def test_open_the_second_one(roots, opened):
    first, second = roots["downloads"] / "a report.pdf", roots["documents"] / "b report.pdf"
    first.write_text("x")
    second.write_text("x")
    os.utime(first, (1000, 1000))
    os.utime(second, (2000, 2000))
    fs_tools.find_file("report")
    fs_tools.open_file("second one")
    assert opened == [str(first)]


def test_open_file_refuses_programs(roots, opened):
    (roots["downloads"] / "setup.exe").write_text("x")
    assert fs_tools.open_file("setup.exe").startswith("I won't run programs")
    assert opened == []


def test_open_file_asks_when_two_files_share_a_name(roots, opened):
    (roots["downloads"] / "notes.txt").write_text("x")
    (roots["documents"] / "notes.txt").write_text("x")
    out = fs_tools.open_file("notes.txt")
    assert isinstance(out, Reply) and out.say.startswith("I found 2 files called notes.txt")
    assert opened == []


def test_open_folder(roots, opened):
    assert fs_tools.open_folder("downloads") == "Opening Downloads."
    assert opened == [str(roots["downloads"])]
    assert fs_tools.open_folder("garage") == "I don't know a folder called garage."


def test_recent_files_newest_first(monkeypatch, tmp_path):
    recent = tmp_path / "Recent"
    recent.mkdir()
    for name, stamp in (("old.docx.lnk", 1000), ("new.pdf.lnk", 3000), ("mid.txt.lnk", 2000)):
        (recent / name).write_text("x")
        os.utime(recent / name, (stamp, stamp))
    monkeypatch.setattr(fs_tools, "_recent_dir", lambda: recent)
    assert fs_tools.recent_files().say == "Recently opened: new.pdf, mid.txt, old.docx."
