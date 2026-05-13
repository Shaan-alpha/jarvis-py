import re
import threading
# pyrefly: ignore [missing-import]
import pyttsx3
# pyrefly: ignore [missing-import]
import speech_recognition as sr


speech_lock = threading.Lock()

current_engine = None

speech_thread = None


def create_engine():

    engine = pyttsx3.init("sapi5")

    voices = engine.getProperty("voices")

    engine.setProperty("voice", voices[1].id)

    rate = engine.getProperty("rate")

    engine.setProperty("rate", rate - 25)

    engine.setProperty("volume", 1.0)

    return engine


def _speak_thread(text):

    global current_engine

    try:

        engine = create_engine()

        current_engine = engine

        engine.say(text)

        engine.runAndWait()

        engine.stop()

    except Exception as e:

        print(f"TTS Error: {e}")

    finally:

        current_engine = None


def speak(text):

    global speech_thread

    try:

        stop_speaking()

        if speech_thread and speech_thread.is_alive():

            speech_thread.join(timeout=0.2)

        print(f"Jarvis: {text}")

        speech_thread = threading.Thread(
            target=_speak_thread,
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

            current_engine.stop()

            current_engine = None

    except Exception as e:

        print(f"Stop Speech Error: {e}")


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

    with sr.Microphone() as source:

        print("Listening...")

        recognizer.dynamic_energy_threshold = True

        recognizer.pause_threshold = 1.2

        recognizer.non_speaking_duration = 0.5

        recognizer.phrase_threshold = 0.3

        recognizer.operation_timeout = 5

        recognizer.adjust_for_ambient_noise(
            source,
            duration=1
        )

        try:

            audio = recognizer.listen(
                source,
                timeout=5,
                phrase_time_limit=5
            )

        except sr.WaitTimeoutError:

            return "none"

    try:

        print("Recognizing...")

        query = recognizer.recognize_google(
            audio,
            language="en-in"
        )

        query = clean_query(query)

        print(f"User said: {query}")

        return query

    except sr.UnknownValueError:

        print("Could not understand audio")

        return "none"

    except sr.RequestError:

        print("Speech recognition service unavailable")

        return "none"

    except Exception as e:

        print(f"Recognition Error: {e}")

        return "none"