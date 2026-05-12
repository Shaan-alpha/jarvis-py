# pyrefly: ignore [missing-import]
import pyttsx3

# pyrefly: ignore [missing-import]
import speech_recognition as sr


def speak(text):

    if not text:
        return

    clean_text = text.replace('"', "").strip()

    try:

        engine = pyttsx3.init("sapi5")

        voices = engine.getProperty("voices")
        engine.setProperty("voice", voices[1].id)

        rate = engine.getProperty("rate")
        engine.setProperty("rate", rate - 40)

        engine.setProperty("volume", 1)

        engine.say(clean_text)
        engine.runAndWait()

    except Exception as e:
        print(f"Speech Error: {e}")

def command():

    r = sr.Recognizer()

    with sr.Microphone() as source:

        print("Listening...", flush=True)

        r.adjust_for_ambient_noise(source, duration=0.3)

        r.pause_threshold = 1.5
        r.phrase_threshold = 0.3
        r.non_speaking_duration = 0.5
        r.energy_threshold = 3000

        try:

            audio = r.listen(
                source,
                timeout=3,
                phrase_time_limit=10
            )

        except sr.WaitTimeoutError:
            return "none"

    try:

        print("Recognizing...", flush=True)

        query = r.recognize_google(
            audio,
            language="en-in"
        )

        print(f"User said: {query}\n")

        return query.lower()

    except sr.UnknownValueError:
        print("Could not understand audio")

    except sr.RequestError:
        print("Speech recognition service unavailable")

    except Exception as e:
        print(f"Recognition Error: {e}")

    return "none"