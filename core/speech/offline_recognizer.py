import json
import os

# pyrefly: ignore [missing-import]
import vosk

from config.settings import (
    VOSK_MODEL_PATH
)

from core.utils.logger import (
    logger
)


vosk.SetLogLevel(-1)


_model = None


def _get_model():

    global _model

    if _model is None:

        if os.path.isdir(VOSK_MODEL_PATH):

            logger.info(
                f"Loading local Vosk model: "
                f"{VOSK_MODEL_PATH}"
            )

            _model = vosk.Model(
                model_path=VOSK_MODEL_PATH
            )

        else:

            logger.info(
                "Local Vosk model missing, "
                "falling back to auto-download"
            )

            _model = vosk.Model(lang="en-us")

    return _model


def recognize_offline(
    recognizer,
    audio
):

    try:

        model = _get_model()

        raw = audio.get_raw_data(
            convert_rate=16000,
            convert_width=2
        )

        kaldi = vosk.KaldiRecognizer(
            model,
            16000
        )

        kaldi.AcceptWaveform(raw)

        result = json.loads(
            kaldi.FinalResult()
        )

        text = result.get("text", "").strip()

        if not text:

            return "none"

        return text

    except Exception as e:

        logger.exception(
            f"Offline STT error: {e}"
        )

        return "none"
