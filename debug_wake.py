"""
Debug the wake-word detector.

Run:
    python debug_wake.py

Prints the live `hey_jarvis` confidence score every audio chunk so you
can see whether the model is hearing you at all.

- If you NEVER see scores above 0.10 when saying "hey jarvis" loudly:
    the mic isn't reaching the model. Check OS mic / default device.
- If scores peak around 0.20-0.40 but never hit 0.50:
    lower WAKE_THRESHOLD in config/settings.py (try 0.30).
- If you see >0.50 spikes when you say "hey jarvis":
    the model works. Your real app threshold is fine.

Press Ctrl+C to quit.
"""

import os
import sys

import numpy as np
import pyaudio

# pyrefly: ignore [missing-import]
from openwakeword.model import Model

from config.settings import (
    WAKE_MODEL_PATH,
    WAKE_THRESHOLD,
    WAKE_WORD
)


FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280


def list_input_devices(pa):

    print("\n=== Available input devices ===")

    default_index = None

    try:

        default_index = pa.get_default_input_device_info()["index"]

    except Exception:

        pass

    for i in range(pa.get_device_count()):

        info = pa.get_device_info_by_index(i)

        if info["maxInputChannels"] > 0:

            marker = "  (default)" if i == default_index else ""

            print(
                f"  [{i}] {info['name']}  "
                f"channels={info['maxInputChannels']}  "
                f"rate={int(info['defaultSampleRate'])}{marker}"
            )


def main():

    print(f"WAKE_WORD            = {WAKE_WORD}")
    print(f"WAKE_THRESHOLD       = {WAKE_THRESHOLD}")
    print(f"WAKE_MODEL_PATH      = {WAKE_MODEL_PATH}")
    print(f"Model exists locally = {os.path.exists(WAKE_MODEL_PATH)}")

    audio = pyaudio.PyAudio()

    list_input_devices(audio)

    print(
        "\nLoading openWakeWord model "
        "(may take a few seconds)..."
    )

    if os.path.exists(WAKE_MODEL_PATH):

        model = Model(
            wakeword_models=[WAKE_MODEL_PATH],
            inference_framework="onnx"
        )

    else:

        model = Model(inference_framework="onnx")

    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    print(
        "\n=== Listening. Say 'hey jarvis' a few times. ==="
    )

    print(
        "Showing audio RMS + wake-word scores live.\n"
    )

    peak_score = 0.0

    try:

        while True:

            audio_data = stream.read(
                CHUNK,
                exception_on_overflow=False
            )

            audio_np = np.frombuffer(
                audio_data,
                dtype=np.int16
            )

            rms = float(
                np.sqrt(np.mean(
                    audio_np.astype(np.float64) ** 2
                ))
            )

            prediction = model.predict(audio_np)

            best_name, best_score = max(
                prediction.items(),
                key=lambda kv: kv[1]
            )

            if best_score > peak_score:

                peak_score = best_score

            bar_len = int(best_score * 40)
            bar = "#" * bar_len + "-" * (40 - bar_len)

            mic_indicator = (
                "MIC OK   " if rms > 200 else "mic quiet"
            )

            line = (
                f"\r{mic_indicator}  "
                f"rms={rms:7.0f}  "
                f"{best_name}={best_score:.3f}  "
                f"|{bar}|  "
                f"peak={peak_score:.3f}"
            )

            sys.stdout.write(line)
            sys.stdout.flush()

            if best_score > WAKE_THRESHOLD:

                print(
                    f"\n*** WAKE WORD DETECTED  "
                    f"({best_name} = {best_score:.3f}) ***\n"
                )

    except KeyboardInterrupt:

        print(
            f"\n\nDone. Peak score during session: "
            f"{peak_score:.3f}"
        )

    finally:

        stream.stop_stream()

        stream.close()

        audio.terminate()


if __name__ == "__main__":

    main()
