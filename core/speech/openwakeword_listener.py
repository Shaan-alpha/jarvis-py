import os

import pyaudio
import numpy as np

# pyrefly: ignore [missing-import]
import openwakeword
# pyrefly: ignore [missing-import]
from openwakeword.model import Model
# pyrefly: ignore [missing-import]
from openwakeword.utils import download_models

from config.settings import (
    INPUT_DEVICE_INDEX,
    WAKE_MODEL_PATH,
    WAKE_THRESHOLD,
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


def detect_wake_word(stop_event=None, verbose=True):

    model = _get_model()

    model.reset()

    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=INPUT_DEVICE_INDEX,
        frames_per_buffer=CHUNK
    )

    if verbose:

        logger.info(
            f"Listening for wake word: '{WAKE_WORD}'"
        )

        print(
            f"\nListening for wake word "
            f"('{WAKE_WORD.replace('_', ' ')}')..."
        )

    try:

        # Drain stale audio + warm the model on fresh silence so a
        # previous session's "hey jarvis" or TTS bleed does not
        # immediately re-trigger detection.

        for _ in range(DRAIN_CHUNKS):

            if stop_event is not None and stop_event.is_set():

                return False

            audio_data = stream.read(
                CHUNK,
                exception_on_overflow=False
            )

            audio_np = np.frombuffer(
                audio_data,
                dtype=np.int16
            )

            model.predict(audio_np)

        while True:

            if stop_event is not None and stop_event.is_set():

                return False

            audio_data = stream.read(
                CHUNK,
                exception_on_overflow=False
            )

            audio_np = np.frombuffer(
                audio_data,
                dtype=np.int16
            )

            rms = float(np.sqrt(np.mean(audio_np.astype(np.float64) ** 2)))

            events.emit("level", rms=min(1.0, rms / 3000.0))

            prediction = model.predict(audio_np)

            for wakeword, score in prediction.items():

                if score > WAKE_THRESHOLD:

                    logger.info(
                        f"Wake word detected: "
                        f"{wakeword} ({score:.2f})"
                    )

                    return True

    finally:

        stream.stop_stream()

        stream.close()

        audio.terminate()
