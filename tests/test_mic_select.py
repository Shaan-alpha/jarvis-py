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


_REALWORLD_DEVICES = [
    {"index": 1, "maxInputChannels": 1,
     "name": "Headset (realme Buds Air7 Pro)", "host": "MME"},
    {"index": 2, "maxInputChannels": 4,
     "name": "Microphone Array (Intel)", "host": "MME"},
    {"index": 8, "maxInputChannels": 4,
     "name": "Microphone Array (Intel)", "host": "Windows DirectSound"},
    {"index": 15, "maxInputChannels": 2,
     "name": "Microphone Array (Intel)", "host": "Windows WASAPI"},
]


def test_select_wake_prefers_wasapi_non_bluetooth():
    # OS default is the Bluetooth headset (1), but the wake word wants the clean
    # WASAPI built-in mic.
    assert checks.select_input_device(
        _REALWORLD_DEVICES, default_index=1, for_wake=True) == 15


def test_select_stt_prefers_mme_non_bluetooth():
    # STT (mono speech_recognition + Google) wants the MME built-in mic, not
    # WASAPI (which gives unintelligible mono on a multi-channel device).
    assert checks.select_input_device(
        _REALWORLD_DEVICES, default_index=1, for_wake=False) == 2


def test_select_avoids_bluetooth_even_on_wasapi():
    devices = [
        {"index": 14, "maxInputChannels": 1,
         "name": "Headset (realme Buds Air7 Pro)", "host": "Windows WASAPI"},
        {"index": 2, "maxInputChannels": 4,
         "name": "Microphone Array (Intel)", "host": "MME"},
    ]
    # A Bluetooth headset on WASAPI still loses to a non-Bluetooth built-in mic,
    # even for the wake word that otherwise prefers WASAPI.
    assert checks.select_input_device(devices, default_index=14, for_wake=True) == 2


def test_select_uses_bluetooth_when_only_input():
    devices = [
        {"index": 1, "maxInputChannels": 1,
         "name": "Headset (realme Buds Air7 Pro)", "host": "MME"},
    ]
    # Least-bad: a Bluetooth mic still beats no microphone at all.
    assert checks.select_input_device(devices, default_index=1) == 1


def test_check_microphone_returns_distinct_wake_and_stt_devices():
    class _FakePyAudio:
        _devices = _REALWORLD_DEVICES
        _hosts = {"MME": "MME", "WASAPI": "Windows WASAPI",
                  "DSOUND": "Windows DirectSound"}

        def PyAudio(self):
            return self

        def get_device_count(self):
            return len(self._devices)

        def get_device_info_by_index(self, i):
            # devices keyed by their 'index'; map position -> device
            return dict(self._devices[i])

        def get_host_api_info_by_index(self, h):
            return {"name": h}      # 'host' already holds the api name string

        def get_default_input_device_info(self):
            return {"index": 1}     # OS default is the Bluetooth headset

        def terminate(self):
            pass

    fake = _FakePyAudio()
    # get_device_info_by_index is called with range(count); align our list so
    # positions 0..3 map to the four devices, and 'hostApi' resolves to the name.
    for d in fake._devices:
        d["hostApi"] = d["host"]

    result = checks.check_microphone(pyaudio_module=fake)
    assert result["ok"] is True
    assert result["index"] == 2         # STT -> MME built-in mic
    assert result["wake_index"] == 15   # wake word -> WASAPI built-in mic


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
        energy_threshold = 300
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
