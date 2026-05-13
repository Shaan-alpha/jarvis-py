import queue
import pyaudio
import numpy as np

# pyrefly: ignore [missing-import]
from openwakeword.model import Model


model = Model(
    wakeword_models=None
)

audio_queue = queue.Queue()


FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280


def detect_wake_word():

    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    print("Waiting for wake word...")

    while True:

        audio_data = stream.read(
            CHUNK,
            exception_on_overflow=False
        )

        audio_np = np.frombuffer(
            audio_data,
            dtype=np.int16
        )

        prediction = model.predict(audio_np)

        for wakeword, score in prediction.items():

            if score > 0.5:

                print(
                    f"Wake word detected: {wakeword}"
                )

                stream.stop_stream()

                stream.close()

                audio.terminate()

                return True