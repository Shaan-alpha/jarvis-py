import json

# pyrefly: ignore [missing-import]
import vosk

from core.utils.logger import (
    logger
)


vosk.SetLogLevel(-1)


_model = None


def _get_model():

    global _model

    if _model is None:

        logger.info(
            "Loading Vosk offline STT model "
            "(downloads ~40MB on first run)"
        )

        _model = vosk.Model(lang="en-us")

    return _model


def warm_up():

    _get_model()


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
