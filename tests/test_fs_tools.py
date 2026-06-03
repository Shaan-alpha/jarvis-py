from core.agent import fs_tools


def _patch_workspace(monkeypatch, tmp_path):
    monkeypatch.setattr(fs_tools, "_workspace", lambda: tmp_path)


def test_resolve_rejects_parent_traversal(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools._resolve_in_workspace("../secrets") is None


def test_resolve_rejects_absolute_path(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools._resolve_in_workspace("/etc/passwd") is None


def test_resolve_rejects_drive_path(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools._resolve_in_workspace(r"C:\Windows\system32") is None


def test_resolve_rejects_empty(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools._resolve_in_workspace("") is None
    assert fs_tools._resolve_in_workspace("   ") is None


def test_resolve_rejects_workspace_root_itself(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools._resolve_in_workspace(".") is None


def test_resolve_accepts_simple_name(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    resolved = fs_tools._resolve_in_workspace("notes.txt")
    assert resolved == (tmp_path / "notes.txt").resolve()


def test_preview_short_returns_verbatim():
    assert fs_tools._preview("hello") == "hello"


def test_preview_long_is_truncated():
    out = fs_tools._preview("x" * 3000)
    assert out.startswith("Your file has")
    assert "3000 characters" in out
    assert out.endswith("(truncated).")
    assert len(out) < 300


def test_list_files_empty(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools.list_files() == "Your workspace is empty."


def test_list_files_lists_names(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.txt").write_text("y")
    out = fs_tools.list_files()
    assert "a.txt" in out
    assert "b.txt" in out


def test_list_files_ignores_directories(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("x")
    out = fs_tools.list_files()
    assert "a.txt" in out
    assert "sub" not in out


def test_read_file_missing(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools.read_file("nope.txt") == \
        "I couldn't find nope.txt in your workspace."


def test_read_file_empty(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "e.txt").write_text("")
    assert fs_tools.read_file("e.txt") == "e.txt is empty."


def test_read_file_short_returns_verbatim(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "s.txt").write_text("hello world")
    assert fs_tools.read_file("s.txt") == "hello world"


def test_read_file_long_is_truncated(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "big.txt").write_text("x" * 3000)
    out = fs_tools.read_file("big.txt")
    assert out.startswith("Your file has")
    assert len(out) < 300


def test_read_file_rejects_traversal(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools.read_file("../../etc/passwd") == \
        "That path is outside my workspace."


def test_write_file_creates_and_confirms(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    out = fs_tools.write_file("a.txt", "hi")
    assert out == "Saved a.txt."
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hi"


def test_write_file_refuses_overwrite(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "a.txt").write_text("original")
    out = fs_tools.write_file("a.txt", "replacement")
    assert out == "a.txt already exists; pick another name."
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "original"


def test_write_file_rejects_traversal(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    out = fs_tools.write_file("../evil.txt", "x")
    assert out == "That path is outside my workspace."
    assert not (tmp_path.parent / "evil.txt").exists()


def test_search_files_hit(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "report-q1.txt").write_text("x")
    (tmp_path / "notes.txt").write_text("y")
    out = fs_tools.search_files("report")
    assert "report-q1.txt" in out
    assert "notes.txt" not in out


def test_search_files_case_insensitive(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "Report.txt").write_text("x")
    out = fs_tools.search_files("report")
    assert "Report.txt" in out


def test_search_files_miss(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "notes.txt").write_text("y")
    assert fs_tools.search_files("invoice") == "No files match invoice."


def test_fs_tools_registered():
    from core.agent import loader, registry
    loader.load_builtins()
    for name in ("list_files", "read_file", "write_file", "search_files"):
        assert registry.get(name) is not None
