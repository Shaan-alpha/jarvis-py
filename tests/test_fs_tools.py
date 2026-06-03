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
