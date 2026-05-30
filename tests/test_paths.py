import sys

import core.paths as paths


def test_is_frozen_false_by_default(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert paths.is_frozen() is False


def test_is_frozen_true_when_sys_frozen_set(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert paths.is_frozen() is True


def test_resource_dir_source_is_repo_root(monkeypatch):
    monkeypatch.setattr(paths, "is_frozen", lambda: False)
    result = paths.resource_dir()
    assert (result / "core").is_dir()
    assert (result / "app.py").is_file()


def test_resource_dir_frozen_is_meipass(monkeypatch, tmp_path):
    # In a PyInstaller one-folder build, bundled data lives in sys._MEIPASS
    # (the _internal/ folder), NOT alongside the executable. resource_dir()
    # must follow _MEIPASS or it resolves one level too high and misses the
    # bundled models/ and hud/web.
    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    meipass = tmp_path / "_internal"
    meipass.mkdir()
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Jarvis.exe"))
    assert paths.resource_dir() == meipass


def test_user_data_dir_source_is_repo_root(monkeypatch):
    monkeypatch.setattr(paths, "is_frozen", lambda: False)
    result = paths.user_data_dir()
    assert (result / "core").is_dir()
    assert (result / "app.py").is_file()


def test_user_data_dir_frozen_raises_without_appdata(monkeypatch):
    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.delenv("APPDATA", raising=False)
    import pytest
    with pytest.raises(RuntimeError):
        paths.user_data_dir()


def test_user_data_dir_frozen_is_appdata(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    result = paths.user_data_dir()
    assert result == tmp_path / "JarvisAI"
    assert result.is_dir()
