import numpy as np

import core.speech.openwakeword_listener as wl


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
