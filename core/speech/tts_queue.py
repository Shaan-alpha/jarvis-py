import queue
import threading
import time

from core.speech.engine import (
    speak_sync,
    stop_speaking
)


tts_queue = queue.Queue()

is_running = False


def tts_worker():

    global is_running

    while is_running:

        try:

            text = tts_queue.get(timeout=1)

        except queue.Empty:

            continue

        try:

            if text:

                speak_sync(text)

        finally:

            tts_queue.task_done()


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


def clear_queue():

    while not tts_queue.empty():

        try:

            tts_queue.get_nowait()

        except queue.Empty:

            break

        try:

            tts_queue.task_done()

        except ValueError:

            pass


def wait_until_done():
    """Block until every queued sentence has been spoken."""

    tts_queue.join()


def wait_until_done_or_barge_in():
    """
    Block until the TTS queue drains, OR the user says the wake word
    again. Returns True if the user interrupted, False if Jarvis
    finished speaking on its own.
    """

    # Late import to avoid a circular dep when the module loads.
    from core.speech.openwakeword_listener import (
        detect_wake_word
    )

    stop_event = threading.Event()
    interrupted = {"value": False}

    def wake_listener():

        try:

            if detect_wake_word(
                stop_event=stop_event,
                verbose=False
            ):

                interrupted["value"] = True

        except Exception:

            pass

    listener_thread = threading.Thread(
        target=wake_listener,
        daemon=True
    )

    listener_thread.start()

    try:

        while tts_queue.unfinished_tasks > 0:

            if interrupted["value"]:

                clear_queue()

                stop_speaking()

                return True

            time.sleep(0.05)

        return False

    finally:

        stop_event.set()

        listener_thread.join(timeout=1.5)
