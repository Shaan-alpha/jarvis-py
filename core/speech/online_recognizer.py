# pyrefly: ignore [missing-import]
import speech_recognition as sr

from core.utils.logger import (
    logger
)


def recognize_online(
    recognizer,
    audio
):

    try:

        return recognizer.recognize_google(
            audio,
            language="en-in"
        )

    except sr.UnknownValueError:

        logger.info(
            "Online STT: could not understand audio"
        )

        return "none"

    except sr.RequestError as e:

        logger.warning(
            f"Online STT unavailable: {e}"
        )

        return None

    except Exception as e:

        logger.exception(
            f"Online STT error: {e}"
        )

        return None
