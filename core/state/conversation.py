"""Short-term conversation state — in RAM only, never written to disk.

Follow-ups ("how tall is he?", "repeat that", "tell me more"), the last file
results ("open the second one") and pending confirmations ("say yes to
confirm") live here. Cleared when the voice session goes to sleep.
"""

import re
import threading
import time

from collections import deque

from dataclasses import dataclass

from typing import Callable


HISTORY_TURNS = 3

REPLY_SNIPPET = 200

CONFIRM_SECONDS = 30


@dataclass
class PendingAction:

    description: str

    run: Callable

    expires_at: float


class Conversation:

    def __init__(self, clock=time.monotonic):

        self._clock = clock

        self._lock = threading.Lock()

        self._reset()

    def _reset(self):

        self._history = deque(maxlen=HISTORY_TURNS)

        self.last_query = ""

        self.last_reply = ""

        self._results = []

        self._pending = None

    def clear(self):

        with self._lock:

            self._reset()

    def add_turn(self, user, reply):

        with self._lock:

            self._history.append((user, (reply or "")[:REPLY_SNIPPET]))

            self.last_query = user

            self.last_reply = reply or ""

    def history(self):

        with self._lock:

            return list(self._history)

    def set_results(self, paths):

        with self._lock:

            self._results = list(paths)

    def results(self):

        with self._lock:

            return list(self._results)

    def set_pending(self, description, run, ttl=CONFIRM_SECONDS):

        with self._lock:

            self._pending = PendingAction(description, run, self._clock() + ttl)

    def has_pending(self):

        with self._lock:

            return self._pending is not None and self._pending.expires_at > self._clock()

    def take_pending(self):
        """The pending action if still valid, removing it either way."""

        with self._lock:

            action, self._pending = self._pending, None

            if action is None or action.expires_at <= self._clock():

                return None

            return action


conversation = Conversation()


_REPEAT = re.compile(r"repeat(?: that| it)?|say (?:that|it) again|what did you (?:just )?say|come again|pardon")

_MORE = re.compile(r"tell me more(?: about (?:it|that))?|explain (?:more|that|it)|more details|go on|elaborate")

_YES = re.compile(r"yes(?: please| do it)?|yeah|yep|sure|confirm|do it|go ahead|ok(?:ay)? do it")

_NO = re.compile(r"no|nope|cancel|dont|do not|stop|never ?mind|forget it")


def match_command(query):
    """'repeat' / 'more' for the conversation controls, else None."""

    if _REPEAT.fullmatch(query or ""):

        return "repeat"

    if _MORE.fullmatch(query or ""):

        return "more"

    return None


def is_yes(query):

    return _YES.fullmatch(query or "") is not None


def is_no(query):

    return _NO.fullmatch(query or "") is not None
