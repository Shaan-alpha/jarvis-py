import queue
import json
# pyrefly: ignore [missing-import]
import sounddevice as sd

# pyrefly: ignore [missing-import]
from vosk import Model, KaldiRecognizer


MODEL_PATH = "models/vosk/vosk-model-small-en-us-0.15"

model = Model(MODEL_PATH)

audio_queue = queue.Queue()


def callback(indata, frames, time, status):

    if status:
        print(status)

    audio_queue.put(bytes(indata))


def listen():

    recognizer = KaldiRecognizer(model, 16000)

    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=callback
    ):

        print("Listening...")

        while True:

            data = audio_queue.get()

            if recognizer.AcceptWaveform(data):

                result = json.loads(
                    recognizer.Result()
                )

                query = result.get("text", "").lower()

                if query:

                    print(f"User said: {query}")

                    return query