import core.paths as paths
import config.settings as settings


def test_vosk_path_under_resource_dir():
    assert str(paths.resource_dir()) in settings.VOSK_MODEL_PATH


def test_wake_path_under_resource_dir():
    assert str(paths.resource_dir()) in settings.WAKE_MODEL_PATH
