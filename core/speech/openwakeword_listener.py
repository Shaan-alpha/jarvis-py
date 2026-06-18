import os

from math import gcd

import pyaudio
import numpy as np

# pyrefly: ignore [missing-import]
from scipy.signal import resample_poly

# pyrefly: ignore [missing-import]
import openwakeword
# pyrefly: ignore [missing-import]
from openwakeword.model import Model
# pyrefly: ignore [missing-import]
from openwakeword.utils import download_models

import config.settings as settings

from config.settings import (
    WAKE_MODEL_PATH,
    WAKE_THRESHOLD,
    WAKE_CONSECUTIVE,
    WAKE_WORD
)

from core.hud import events

from core.utils.logger import (
    logger
)


FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280


def _resample_to_16k(samples, src_rate):
    """Resample mono int16 PCM from `src_rate` to 16kHz (what openWakeWord needs).

    Force-opening a 44.1/48kHz mic at 16kHz (PyAudio + MME on Windows) yields
    degraded audio that openWakeWord scores near zero — so capture at the device's
    native rate and resample here instead. Verified: the same "hey jarvis" that
    scored ~0 force-opened at 16kHz scores ~0.97 when captured native + resampled.
    """

    if src_rate == RATE:

        return samples

    divisor = gcd(int(src_rate), RATE)

    up = RATE // divisor

    down = int(src_rate) // divisor

    resampled = resample_poly(samples.astype(np.float64), up, down)

    return resampled.astype(np.int16)


_model = None


def _package_model_path():

    base = os.path.dirname(
        os.path.abspath(openwakeword.__file__)
    )

    return os.path.join(
        base,
        "resources",
        "models",
        f"{WAKE_WORD}_v0.1.onnx"
    )


def _resolve_model_path():

    if os.path.exists(WAKE_MODEL_PATH):

        return WAKE_MODEL_PATH

    package_path = _package_model_path()

    if os.path.exists(package_path):

        return package_path

    logger.info(
        f"Downloading wake-word model: {WAKE_WORD}"
    )

    download_models([WAKE_WORD])

    return package_path


def _get_model():

    global _model

    if _model is None:

        path = _resolve_model_path()

        logger.info(
            f"Loading wake-word model: {path}"
        )

        _model = Model(
            wakeword_models=[path],
            inference_framework="onnx"
        )

    return _model


DRAIN_CHUNKS = 12


def _device_format(audio, device_index):
    """The input device's native (sample_rate, channels). PyAudio delivers clean
    audio at the native rate; resampling to 16kHz and the mono downmix happen in
    software — force-opening at 16kHz corrupts the audio for openWakeWord."""

    if device_index is None:

        info = audio.get_default_input_device_info()

    else:

        info = audio.get_device_info_by_index(device_index)

    return int(info["defaultSampleRate"]), max(1, int(info.get("maxInputChannels", 1)))


def _frame_stream(stream, src_rate, read_size, channels):
    """Yield resampled-16kHz, mono, CHUNK-sized openWakeWord frames from `stream`,
    downmixing multi-channel audio and reading as many native blocks as each
    frame needs."""

    pending = np.empty(0, dtype=np.int16)

    while True:

        while len(pending) < CHUNK:

            data = stream.read(read_size, exception_on_overflow=False)

            block = np.frombuffer(data, dtype=np.int16)

            if channels > 1:

                block = block.reshape(-1, channels).mean(axis=1).astype(np.int16)

            pending = np.concatenate([pending, _resample_to_16k(block, src_rate)])

        yield pending[:CHUNK]

        pending = pending[CHUNK:]


def detect_wake_word(stop_event=None, verbose=True):

    model = _get_model()

    model.reset()

    audio = pyaudio.PyAudio()

    # Capture at the device's native rate, then resample to 16kHz in software.
    # Force-opening a 44.1/48kHz mic at 16kHz (PyAudio + MME on Windows) corrupts
    # the audio so openWakeWord never crosses threshold; native capture +
    # _resample_to_16k restores detection.
    # Wake word listens on its own (WASAPI-preferred) device; falls back to the
    # STT/default device when no separate wake device was chosen.
    device_index = settings.WAKE_DEVICE_INDEX

    if device_index is None:

        device_index = settings.INPUT_DEVICE_INDEX

    src_rate, channels = _device_format(audio, device_index)

    read_size = max(1, int(src_rate * 0.08))   # ~80ms native blocks

    stream = audio.open(
        format=FORMAT,
        channels=channels,
        rate=src_rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=read_size
    )

    if verbose:

        logger.info(
            f"Listening for wake word: '{WAKE_WORD}' "
            f"(mic {device_index} @ {src_rate}Hz x{channels}ch -> {RATE}Hz)"
        )

        print(
            f"\nListening for wake word "
            f"('{WAKE_WORD.replace('_', ' ')}')..."
        )

    # Resampled-16kHz mono frame generator (CHUNK samples per frame).
    frames = _frame_stream(stream, src_rate, read_size, channels)

    try:

        # Drain stale audio + warm the model on fresh silence so a
        # previous session's "hey jarvis" or TTS bleed does not
        # immediately re-trigger detection.

        for _ in range(DRAIN_CHUNKS):

            if stop_event is not None and stop_event.is_set():

                return False

            model.predict(next(frames))

        # Consecutive frames above threshold required to fire (debounce).
        streak = 0

        while True:

            if stop_event is not None and stop_event.is_set():

                return False

            audio_np = next(frames)

            rms = float(np.sqrt(np.mean(audio_np.astype(np.float64) ** 2)))

            events.emit("level", rms=min(1.0, rms / 3000.0))

            prediction = model.predict(audio_np)

            best = max(prediction.items(), key=lambda kv: kv[1], default=(None, 0.0))

            wakeword, score = best

            if score > WAKE_THRESHOLD:

                streak += 1

                if streak >= WAKE_CONSECUTIVE:

                    logger.info(
                        f"Wake word detected: "
                        f"{wakeword} ({score:.2f})"
                    )

                    return True

            else:

                streak = 0

    finally:

        stream.stop_stream()

        stream.close()

        audio.terminate()
