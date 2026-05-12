import pyttsx3
import speech_recognition as sr

def initialize_engine():
    engine = pyttsx3.init("sapi5")
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[1].id)
    rate = engine.getProperty('rate')
    engine.setProperty('rate', rate - 50)
    volume = engine.getProperty('volume')
    engine.setProperty('volume', volume + 0.25)
    return engine

def speak(text):
    engine = initialize_engine()
    engine.say(text)
    engine.runAndWait()

def command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        print("Listening.......", end="", flush=True)
        r.pause_threshold = 1.0
        r.phrase_threshold = 0.3
        r.sample_rate = 48000
        r.dynamic_energy_threshold = True
        r.operation_timeout = 5
        r.non_speaking_duration = 0.5
        r.dynamic_energy_adjustment = 2
        r.energy_threshold = 4000
        r.phrase_time_limit = 10
        audio = r.listen(source)
    try:
        print("\r", end="", flush=True)
        print("Recognizing......", end="", flush=True)
        query = r.recognize_google(audio, language='en-in')
        print("\r", end="", flush=True)
        print(f"User said : {query}\n")
    except Exception as e:
        print("Say that again please")
        return "None"
    return query
