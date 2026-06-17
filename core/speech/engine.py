# pyrefly: ignore [missing-import]

import re
import socket
import threading
import time

# pyrefly: ignore [missing-import]
import pyttsx3
# pyrefly: ignore [missing-import]
import speech_recognition as sr

import config.settings as settings

from config.settings import (
    ONLINE_CACHE_TTL,
    ONLINE_CHECK_HOST,
    ONLINE_CHECK_PORT,
    ONLINE_CHECK_TIMEOUT,
    VOICE_RATE,
    VOICE_VOLUME
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


_online_cache = {
    "value": None,
    "checked_at": 0.0
}


def is_online():

    now = time.time()

    cached = _online_cache["value"]

    if (
        cached is not None
        and now - _online_cache["checked_at"]
        < ONLINE_CACHE_TTL
    ):

        return cached

    try:

        with socket.create_connection(
            (ONLINE_CHECK_HOST, ONLINE_CHECK_PORT),
            timeout=ONLINE_CHECK_TIMEOUT
        ):

            online = True

    except OSError:

        online = False

    _online_cache["value"] = online
    _online_cache["checked_at"] = now

    return online


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


# Per-thread persistent pyttsx3 engine. SAPI engines have thread affinity, so
# each speaking thread keeps its own; the long-lived TTS-queue worker thus reuses
# one engine across all streamed sentences instead of re-initialising per
# sentence (the hot path). Ephemeral speak() threads still create one per call.
_engines = threading.local()


def _get_thread_engine():
    """This thread's persistent engine, created once and reused thereafter."""

    engine = getattr(_engines, "engine", None)

    if engine is None:

        engine = create_engine()

        _engines.engine = engine

    return engine


def _drop_thread_engine():
    """Discard this thread's engine so the next call re-initialises it."""

    _engines.engine = None


def _speak_thread(text):

    global current_engine

    try:

        engine = _get_thread_engine()

        current_engine = engine

        engine.say(text)

        engine.runAndWait()

    except Exception as e:

        # Drop the (possibly wedged) engine so the next call re-inits — preserves
        # the old per-call crash-recovery while reusing on the happy path.
        logger.exception(f"TTS error, will re-init next call: {e}")

        _drop_thread_engine()

    finally:

        current_engine = None


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


def clean_query(query):

    query = query.lower().strip()

    query = re.sub(
        r"[^a-zA-Z0-9\s]",
        "",
        query
    )

    query = re.sub(
        r"\s+",
        " ",
        query
    )

    return query


def command():

    recognizer = sr.Recognizer()

    with sr.Microphone(device_index=settings.INPUT_DEVICE_INDEX) as source:

        print("Listening...")

        recognizer.dynamic_energy_threshold = True

        # Phrase-end detection. The previous 0.8s pause cut short multi-word
        # phrases ("how are you" -> "how") because the natural gap between
        # spoken words exceeded it. 1.2s tolerates inter-word pauses so the
        # whole utterance is captured; non_speaking_duration must stay <=
        # pause_threshold (it's the trailing silence kept with the phrase).
        recognizer.pause_threshold = 1.2

        recognizer.non_speaking_duration = 0.6

        recognizer.phrase_threshold = 0.2

        recognizer.operation_timeout = 8

        recognizer.adjust_for_ambient_noise(
            source,
            duration=0.5
        )

        # Ambient calibration can over-raise the threshold (noisy room / TTS
        # tail), making Jarvis ignore normal speech. Cap it so quiet speech is
        # still heard; dynamic_energy_threshold keeps adapting from here.
        calibrated = recognizer.energy_threshold

        if calibrated > settings.MAX_ENERGY_THRESHOLD:

            recognizer.energy_threshold = settings.MAX_ENERGY_THRESHOLD

        logger.info(
            f"STT energy_threshold: calibrated={calibrated:.0f} "
            f"using={recognizer.energy_threshold:.0f}"
        )

        try:

            audio = recognizer.listen(
                source,
                timeout=6,
                phrase_time_limit=12
            )

        except sr.WaitTimeoutError:

            logger.info("STT: no speech detected (listen timed out)")

            return "none"

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

    return clean_query(result)
