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


def test_engine_reads_live_input_device_index(monkeypatch):
    import config.settings as settings
    import core.speech.engine as se

    # simulate app startup choosing device 7 AFTER import
    monkeypatch.setattr(settings, "INPUT_DEVICE_INDEX", 7)

    captured = {}

    class _FakeSource:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_mic(device_index=None):
        captured["idx"] = device_index
        return _FakeSource()

    # Patch sr.Microphone where engine.py looks it up
    monkeypatch.setattr(se.sr, "Microphone", fake_mic)

    # Patch the recognizer so command() returns quickly without real audio
    class _FakeRec:
        def __init__(self): pass
        dynamic_energy_threshold = True
        pause_threshold = 0
        non_speaking_duration = 0
        phrase_threshold = 0
        operation_timeout = 0

        def adjust_for_ambient_noise(self, source, duration=0): pass

        def listen(self, source, timeout=0, phrase_time_limit=0):
            raise se.sr.WaitTimeoutError()

    monkeypatch.setattr(se.sr, "Recognizer", _FakeRec)

    result = se.command()
    assert captured["idx"] == 7   # live value, not the import-time None
    assert result == "none"       # WaitTimeoutError path returns "none"
