import queue
import json
# pyrefly: ignore [missing-import]
import sounddevice as sd

# pyrefly: ignore [missing-import]
from vosk import Model, KaldiRecognizer


MODEL_PATH = "models/vosk-model"

model = Model(MODEL_PATH)

samplerate = 16000

q = queue.Queue()


def callback(indata, frames, time, status):

    if status:
        print(status)

    q.put(bytes(indata))


def listen():

    recognizer = KaldiRecognizer(model, samplerate)

    with sd.RawInputStream(
        samplerate=samplerate,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=callback
    ):

        print("Listening...")

        while True:

            data = q.get()

            if recognizer.AcceptWaveform(data):

                result = json.loads(
                    recognizer.Result()
                )

                text = result.get("text", "").strip()

                if text:
                    print(f"User said: {text}\n")
                    return text.lower()