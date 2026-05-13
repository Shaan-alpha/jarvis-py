import queue
import threading

from core.speech.engine import speak


tts_queue = queue.Queue()

is_running = False


def tts_worker():

    global is_running

    while is_running:

        try:

            text = tts_queue.get(timeout=1)

            if text:

                speak(text)

        except Exception:
            pass


def start_tts_queue():

    global is_running

    if is_running:
        return

    is_running = True

    thread = threading.Thread(
        target=tts_worker,
        daemon=True
    )

    thread.start()


def stop_tts_queue():

    global is_running

    is_running = False


def add_to_queue(text):

    tts_queue.put(text)