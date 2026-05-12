# pyrefly: ignore [missing-import]
import pyttsx3

engine = pyttsx3.init("sapi5")

engine.say("Hello Shaan. Jarvis voice test successful.")
engine.runAndWait()