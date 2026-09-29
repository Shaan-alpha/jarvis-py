import sys

import pytest

from core.agent.known_folders import known_folders


def test_existing_folders_are_returned_with_the_workspace(tmp_path):
    (tmp_path / "Dl").mkdir()

    def resolver(name, folder_id):
        return str(tmp_path / "Dl") if name == "downloads" else str(tmp_path / "missing")

    folders = known_folders(workspace=tmp_path / "ws", resolver=resolver)
    assert folders == {"downloads": (tmp_path / "Dl").resolve(), "workspace": (tmp_path / "ws").resolve()}


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Known Folders")
def test_real_downloads_folder_resolves_on_windows(tmp_path):
    folders = known_folders(workspace=tmp_path)
    assert folders["downloads"].is_dir()
