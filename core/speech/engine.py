import re
# pyrefly: ignore [missing-import]
import pyttsx3
# pyrefly: ignore [missing-import]
import speech_recognition as sr


def create_engine():

    engine = pyttsx3.init("sapi5")

    voices = engine.getProperty("voices")

    engine.setProperty("voice", voices[1].id)

    rate = engine.getProperty("rate")

    engine.setProperty("rate", rate - 25)

    engine.setProperty("volume", 1.0)

    return engine


def speak(text):

    try:

        print(f"Jarvis: {text}")

        engine = create_engine()

        engine.say(text)

        engine.runAndWait()

        engine.stop()

    except Exception as e:

        print(f"TTS Error: {e}")


def clean_query(query):

    query = query.lower().strip()

    # Remove special characters
    query = re.sub(r"[^a-zA-Z0-9\s]", "", query)

    # Remove extra spaces
    query = re.sub(r"\s+", " ", query)

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