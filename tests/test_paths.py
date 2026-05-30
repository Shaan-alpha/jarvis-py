import sys

from pathlib import Path

import core.paths as paths


def test_is_frozen_false_by_default(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert paths.is_frozen() is False


def test_is_frozen_true_when_sys_frozen_set(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert paths.is_frozen() is True


def test_resource_dir_source_is_repo_root(monkeypatch):
    monkeypatch.setattr(paths, "is_frozen", lambda: False)
    expected = Path(paths.__file__).resolve().parent.parent
    assert paths.resource_dir() == expected


def test_resource_dir_frozen_is_exe_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    fake_exe = tmp_path / "Jarvis.exe"
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    assert paths.resource_dir() == tmp_path
