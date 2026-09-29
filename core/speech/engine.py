# pyrefly: ignore [missing-import]

import threading

# pyrefly: ignore [missing-import]
import pyttsx3
# pyrefly: ignore [missing-import]
import speech_recognition as sr

import config.settings as settings

from config.settings import (
    VOICE_RATE,
    VOICE_VOLUME
)

from core.net import (  # noqa: F401  (re-exported: callers import it from here)
    is_online
)

from core.speech.online_recognizer import (
    recognize_online
)

from core.speech.offline_recognizer import (
    recognize_offline
)

from core.utils.logger import (
    logger
)


speech_lock = threading.Lock()

current_engine = None

speech_thread = None


def create_engine():

    # No driver arg -> pyttsx3 auto-selects the platform driver
    # (sapi5 on Windows, nsss on macOS, espeak on Linux).
    engine = pyttsx3.init()

    voices = engine.getProperty("voices")

    if voices:

        # Prefer the second voice (often a different/female voice on
        # Windows SAPI5) but fall back to the first if unavailable.
        voice_index = 1 if len(voices) > 1 else 0

        engine.setProperty(
            "voice",
            voices[voice_index].id
        )

    rate = engine.getProperty("rate")

    engine.setProperty(
        "rate",
        rate + VOICE_RATE
    )

    engine.setProperty(
        "volume",
        VOICE_VOLUME
    )

    return engine


def _speak_thread(text):
    """Speak one utterance on a freshly-created engine, then dispose it.

    A pyttsx3/SAPI engine reused across multiple ``runAndWait()`` calls only
    produces audio the FIRST time and is silent thereafter (v3.5 PR #12 reused a
    persistent per-thread engine and made the long-lived TTS-queue worker
    inaudible after its first sentence). Creating a fresh engine per utterance —
    the proven pre-v3.5 behaviour — keeps every sentence audible; the init cost is
    small next to staying audible, and dropping the reference in `finally` lets
    pyttsx3 hand back a new engine on the next call.
    """

    global current_engine

    engine = None

    try:

        engine = create_engine()

        current_engine = engine

        engine.say(text)

        engine.runAndWait()

    except Exception as e:

        logger.exception(f"TTS error: {e}")

    finally:

        current_engine = None

        engine = None


def speak_sync(text):
    """Speak `text` and block until it has finished playing."""

    with speech_lock:

        _speak_thread(text)


def speak(text):

    global speech_thread

    try:

        stop_speaking()

        if speech_thread and speech_thread.is_alive():

            speech_thread.join(timeout=0.2)

        # Route through speak_sync (which holds speech_lock) so this async
        # utterance can't run a second pyttsx3 engine concurrently with the
        # TTS-queue worker (which also speaks via speak_sync). stop_speaking()
        # above still cuts the current engine first, preserving barge-in.
        speech_thread = threading.Thread(
            target=speak_sync,
            args=(text,),
            daemon=True
        )

        speech_thread.start()

    except Exception as e:

        print(f"Speak Error: {e}")


def stop_speaking():

    global current_engine

    try:

        if current_engine:

            logger.info("stop_speaking: stopping current engine")

            current_engine.stop()

            current_engine = None

        else:

            logger.info("stop_speaking: no active engine")

    except Exception as e:

        logger.warning(f"stop_speaking failed (cross-thread?): {e}")


# Ambient calibration is done once per wake, not before every turn: it cost
# 0.5s of listening each time and could swallow the start of what you said.
_calibration = {
    "needed": True,
    "threshold": None,
}


def request_calibration():
    """Re-measure room noise on the next listen (called on each wake)."""

    _calibration["needed"] = True


def _prepare_listen(recognizer, source):
    """Tune phrase detection and set the energy threshold for one listen."""

    recognizer.dynamic_energy_threshold = True

    # Silence that ends an utterance; non_speaking_duration must stay <=
    # pause_threshold (it's the trailing silence kept with the phrase).
    recognizer.pause_threshold = settings.STT_PAUSE_SECONDS

    recognizer.non_speaking_duration = min(0.5, settings.STT_PAUSE_SECONDS)

    recognizer.phrase_threshold = 0.2

    recognizer.operation_timeout = 8

    if _calibration["needed"] or _calibration["threshold"] is None:

        recognizer.adjust_for_ambient_noise(source, duration=0.5)

        calibrated = recognizer.energy_threshold

        # Calibration can over-raise the threshold (noisy room / TTS tail),
        # making Jarvis ignore normal speech. Cap it so quiet speech is heard.
        recognizer.energy_threshold = min(calibrated, settings.MAX_ENERGY_THRESHOLD)

        _calibration["needed"] = False

        logger.info(
            f"STT energy_threshold: calibrated={calibrated:.0f} "
            f"using={recognizer.energy_threshold:.0f}"
        )

    else:

        recognizer.energy_threshold = _calibration["threshold"]

    _calibration["threshold"] = recognizer.energy_threshold


def command():

    recognizer = sr.Recognizer()

    with sr.Microphone(device_index=settings.INPUT_DEVICE_INDEX) as source:

        print("Listening...")

        _prepare_listen(recognizer, source)

        try:

            audio = recognizer.listen(
                source,
                timeout=6,
                phrase_time_limit=settings.STT_PHRASE_LIMIT
            )

        except sr.WaitTimeoutError:

            logger.info("STT: no speech detected (listen timed out)")

            return "none"

        # Keep the threshold the dynamic adjustment settled on for next turn,
        # still capped so quiet speech stays audible.
        _calibration["threshold"] = min(recognizer.energy_threshold, settings.MAX_ENERGY_THRESHOLD)

    online = is_online()

    mode = "online" if online else "offline"

    print(f"Recognizing ({mode})...")

    if online:

        result = recognize_online(
            recognizer,
            audio
        )

        if result is None:

            logger.info(
                "Online STT unreachable, "
                "falling back to offline"
            )

            result = recognize_offline(
                recognizer,
                audio
            )

    else:

        result = recognize_offline(
            recognizer,
            audio
        )

    logger.info(f"STT ({mode}) heard: {result!r}")

    if not result or result == "none":

        return "none"

    # Raw text: the caller normalizes for matching and keeps this for content
    # (case, punctuation, "notes.txt") — stripping it here broke both.
    return result.strip()
