import numpy as np
import pytest

import core.speech.openwakeword_listener as wl


class _StubModel:

    def reset(self):
        pass

    def predict(self, frame):
        return {}


def test_pyaudio_is_released_when_the_mic_cannot_be_opened(monkeypatch):
    # The voice loop calls detect_wake_word in a retry-forever loop, so a mic
    # that another app is holding gets re-opened every second. Opening happens
    # before the try/finally that terminates PyAudio, so each failed attempt used
    # to strand a PortAudio instance (and its device handles) for the life of the
    # process. The error must still propagate — the loop relies on it, since it
    # ignores the return value and would otherwise announce a false wake.
    terminated = {"count": 0}

    class _FailingPyAudio:

        def get_device_info_by_index(self, index):
            return {"defaultSampleRate": 48000, "maxInputChannels": 1}

        def get_default_input_device_info(self):
            return {"defaultSampleRate": 48000, "maxInputChannels": 1}

        def open(self, **kwargs):
            raise OSError("[Errno -9996] Invalid input device")

        def terminate(self):
            terminated["count"] += 1

    monkeypatch.setattr(wl.pyaudio, "PyAudio", _FailingPyAudio)

    monkeypatch.setattr(wl, "_get_model", lambda: _StubModel())

    with pytest.raises(OSError):

        wl.detect_wake_word()

    assert terminated["count"] == 1


def test_resample_passthrough_when_already_16k():
    samples = np.zeros(1280, dtype=np.int16)

    out = wl._resample_to_16k(samples, 16000)

    assert out.dtype == np.int16
    assert len(out) == 1280


def test_resample_44100_to_16000_length_ratio():
    # 80ms at 44.1kHz (3528 samples) resamples to 80ms at 16kHz (1280 samples).
    src = np.zeros(3528, dtype=np.int16)

    out = wl._resample_to_16k(src, 44100)

    assert out.dtype == np.int16
    assert abs(len(out) - 1280) <= 2


def test_resample_preserves_tone_frequency():
    # A 440Hz tone captured at 48kHz must still read as ~440Hz after the
    # resample to 16kHz — proves we move the signal, not just its length.
    rate = 48000

    t = np.arange(rate) / rate                       # one second

    tone = (np.sin(2 * np.pi * 440 * t) * 10000).astype(np.int16)

    out = wl._resample_to_16k(tone, rate)

    assert out.dtype == np.int16
    assert abs(len(out) - 16000) <= 2

    spectrum = np.abs(np.fft.rfft(out.astype(np.float64)))
    freqs = np.fft.rfftfreq(len(out), 1 / 16000)
    peak = freqs[int(np.argmax(spectrum))]

    assert abs(peak - 440) < 10
