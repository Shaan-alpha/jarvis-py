import os
import subprocess
import sys

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


def test_move_file_into_a_known_folder(roots):
    src = roots["downloads"] / "report.pdf"
    src.write_text("x")
    assert fs_tools.move_file("report", "documents") == "Moved report.pdf to Documents."
    assert (roots["documents"] / "report.pdf").exists() and not src.exists()


def test_move_to_an_unknown_folder(roots):
    (roots["downloads"] / "report.pdf").write_text("x")
    assert fs_tools.move_file("report", "garage") == "I don't know a folder called garage."


def test_rename_keeps_the_extension(roots):
    (roots["documents"] / "draft.txt").write_text("x")
    assert fs_tools.rename_file("draft", "final") == "Renamed draft.txt to final.txt."
    assert (roots["documents"] / "final.txt").exists()


def test_rename_refuses_to_overwrite(roots):
    (roots["documents"] / "a.txt").write_text("x")
    (roots["documents"] / "b.txt").write_text("y")
    assert fs_tools.rename_file("a", "b") == "b.txt already exists there."


@pytest.mark.parametrize("bad", ["../evil", "..\\evil", "con:x", ""])
def test_rename_rejects_path_tricks(roots, bad):
    (roots["documents"] / "draft.txt").write_text("x")
    assert fs_tools.rename_file("draft", bad) == "That isn't a valid file name."


def test_delete_asks_first_and_recycles_only_on_yes(roots, monkeypatch):
    trashed = []
    monkeypatch.setattr(fs_tools, "send2trash", trashed.append)
    src = roots["downloads"] / "report.pdf"
    src.write_text("x")
    assert fs_tools.delete_file("report") == \
        "Move report.pdf from Downloads to the Recycle Bin? Say yes to confirm."
    assert trashed == [] and src.exists()
    assert conversation.take_pending().run() == "Moved report.pdf to the Recycle Bin."
    assert trashed == [str(src)]


def test_delete_with_two_matches_asks_which_and_sets_no_confirmation(roots):
    (roots["downloads"] / "report.pdf").write_text("x")
    (roots["documents"] / "report.pdf").write_text("x")
    out = fs_tools.delete_file("report")
    assert isinstance(out, Reply) and "2 files" in out.say
    assert conversation.has_pending() is False


# --- final-review fixes -------------------------------------------------------

def test_rename_asks_before_acting_on_a_near_match(roots):
    (roots["documents"] / "resort.pdf").write_text("x")
    assert fs_tools.rename_file("report", "final") == \
        "I couldn't find report exactly. Did you mean resort.pdf? Say yes to rename it."
    assert (roots["documents"] / "resort.pdf").exists()
    assert conversation.take_pending().run() == "Renamed resort.pdf to final.pdf."


def test_move_asks_before_acting_on_a_near_match(roots):
    (roots["downloads"] / "resort.pdf").write_text("x")
    assert fs_tools.move_file("report", "documents") == \
        "I couldn't find report exactly. Did you mean resort.pdf? Say yes to move it."
    assert (roots["downloads"] / "resort.pdf").exists()


def test_delete_it_uses_the_file_just_found(roots, monkeypatch):
    monkeypatch.setattr(fs_tools, "send2trash", lambda path: None)
    (roots["downloads"] / "report.pdf").write_text("x")
    (roots["documents"] / "kit.txt").write_text("x")
    fs_tools.find_file("report")
    assert fs_tools.delete_file("it") == \
        "Move report.pdf from Downloads to the Recycle Bin? Say yes to confirm."


def test_rename_it_uses_the_file_just_found(roots):
    (roots["downloads"] / "report.pdf").write_text("x")
    (roots["documents"] / "kit.txt").write_text("x")
    fs_tools.find_file("report")
    assert fs_tools.rename_file("it", "budget") == "Renamed report.pdf to budget.pdf."
    assert (roots["documents"] / "kit.txt").exists()


def test_move_the_second_one_uses_the_results(roots):
    first, second = roots["downloads"] / "a report.pdf", roots["downloads"] / "b report.pdf"
    first.write_text("x")
    second.write_text("x")
    os.utime(first, (2000, 2000))
    os.utime(second, (1000, 1000))
    fs_tools.find_file("report")
    assert fs_tools.move_file("second one", "documents") == "Moved b report.pdf to Documents."


def test_a_pronoun_with_nothing_found_asks_which_file(roots):
    (roots["documents"] / "kit.txt").write_text("x")
    assert fs_tools.delete_file("it") == "Which file? Say 'find' and its name first."
    assert conversation.has_pending() is False


def test_symlinked_folders_are_not_followed_out_of_the_roots(roots, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret_plan.txt").write_text("x")
    try:
        os.symlink(outside, roots["documents"] / "linked", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks need privileges here")
    assert fs_tools.find_file("secret plan") == "I couldn't find secret plan."


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junctions")
def test_directory_junctions_are_not_followed_out_of_the_roots(roots, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret_plan.txt").write_text("x")
    subprocess.run(["cmd", "/c", "mklink", "/J", str(roots["documents"] / "linked"), str(outside)],
                   check=True, capture_output=True)
    assert fs_tools.find_file("secret plan") == "I couldn't find secret plan."


@pytest.mark.skipif(sys.platform != "win32", reason="Windows hidden attribute")
def test_hidden_folders_are_skipped(roots):
    import ctypes
    hidden = roots["documents"] / "stash"
    hidden.mkdir()
    (hidden / "budget.xlsx").write_text("x")
    ctypes.windll.kernel32.SetFileAttributesW(str(hidden), 0x2)
    assert fs_tools.find_file("budget") == "I couldn't find budget."
