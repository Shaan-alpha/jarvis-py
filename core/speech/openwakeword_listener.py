import os

import pyaudio
import numpy as np

# pyrefly: ignore [missing-import]
from openwakeword.model import Model
# pyrefly: ignore [missing-import]
from openwakeword.utils import download_models
# pyrefly: ignore [missing-import]
import openwakeword

from config.settings import (
    WAKE_THRESHOLD
)

from core.utils.logger import (
    logger
)


WAKE_WORD = "hey_jarvis"

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280


def _model_path():

    base = os.path.dirname(
        os.path.abspath(openwakeword.__file__)
    )

    return os.path.join(
        base,
        "resources",
        "models",
        f"{WAKE_WORD}_v0.1.onnx"
    )


def _ensure_model():

    path = _model_path()

    if os.path.exists(path):

        return

    logger.info(
        f"Downloading wake-word model: "
        f"{WAKE_WORD}"
    )

    download_models([WAKE_WORD])


_ensure_model()


_model = Model(
    wakeword_models=[_model_path()],
    inference_framework="onnx"
)


def detect_wake_word():

    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    logger.info(
        f"Listening for wake word: "
        f"'{WAKE_WORD}'"
    )

    print(
        f"\nListening for wake word "
        f"('{WAKE_WORD.replace('_', ' ')}')..."
    )

    try:

        while True:

            audio_data = stream.read(
                CHUNK,
                exception_on_overflow=False
            )

            audio_np = np.frombuffer(
                audio_data,
                dtype=np.int16
            )

            prediction = _model.predict(
                audio_np
            )

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
