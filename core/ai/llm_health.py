"""Remembers that Ollama just failed, so the next queries answer at once.

Without this, every query with Ollama down or out of memory paid decide_tool's
timeout and then ask_llm's before saying so. The state expires on its own.
"""

import threading
import time

from config.settings import (
    LLM_DOWN_SECONDS
)


_lock = threading.Lock()

_state = {
    "down_until": 0.0,
    "reason": "",
}

_STILL_WORKS = "I can still tell the time, do maths, find files and set reminders."


def mark_down(reason, now=None):

    now = time.monotonic() if now is None else now

    with _lock:

        _state["down_until"] = now + LLM_DOWN_SECONDS

        _state["reason"] = str(reason or "")


def mark_up():

    with _lock:

        _state["down_until"] = 0.0

        _state["reason"] = ""


def is_down(now=None):

    now = time.monotonic() if now is None else now

    with _lock:

        return now < _state["down_until"]


def down_reason():

    with _lock:

        return _state["reason"]


def unavailable_message():
    """One line: why the model can't answer, and what still works."""

    if "memory" in down_reason().lower():

        return f"My language model needs more free memory than this PC has right now. {_STILL_WORKS}"

    return f"My language model isn't available right now. {_STILL_WORKS}"
