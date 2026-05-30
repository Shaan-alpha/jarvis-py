import config.settings as settings
import core.setup.checks as checks


def test_select_returns_default_when_input_capable():
    devices = [
        {"index": 0, "maxInputChannels": 0},
        {"index": 1, "maxInputChannels": 2},
    ]
    assert checks.select_input_device(devices, default_index=1) == 1


def test_select_falls_back_to_first_input():
    devices = [
        {"index": 0, "maxInputChannels": 0},
        {"index": 2, "maxInputChannels": 1},
    ]
    assert checks.select_input_device(devices, default_index=0) == 2


def test_select_returns_none_when_no_input():
    devices = [{"index": 0, "maxInputChannels": 0}]
    assert checks.select_input_device(devices, default_index=0) is None


def test_check_microphone_returns_index_for_found_device():
    class _FakePyAudio:
        def PyAudio(self):
            return self

        def get_device_count(self):
            return 1

        def get_device_info_by_index(self, i):
            return {"index": 0, "maxInputChannels": 2}

        def get_default_input_device_info(self):
            return {"index": 0}

        def terminate(self):
            pass

    result = checks.check_microphone(pyaudio_module=_FakePyAudio())
    assert result["ok"] is True
    assert result["index"] == 0


def test_check_microphone_no_input_device():
    class _FakePyAudio:
        def PyAudio(self):
            return self

        def get_device_count(self):
            return 1

        def get_device_info_by_index(self, i):
            return {"index": 0, "maxInputChannels": 0}

        def get_default_input_device_info(self):
            raise OSError("no default")

        def terminate(self):
            pass

    result = checks.check_microphone(pyaudio_module=_FakePyAudio())
    assert result["ok"] is False


def test_input_device_index_setting_exists():
    assert hasattr(settings, "INPUT_DEVICE_INDEX")
    assert settings.INPUT_DEVICE_INDEX is None
