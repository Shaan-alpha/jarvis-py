"""Per-turn latency instrumentation.

`Timeline` is a pure value object: record named stage marks, ask for deltas /
total / a one-line summary. The module also exposes a thread-local "current
timeline" (`start_turn`/`mark`/`end_turn`) so the pipeline — which spans
app.process_query, ollama_engine, and tts_queue across threads — can mark stages
without threading a Timeline through every call signature.

Behaviour-neutral and cheap (perf_counter); safe to leave always on. `mark` and
`end_turn` are no-ops when no turn is active, so callers never need to guard.
"""

import threading
import time

from core.hud import events

from core.utils.logger import (
    logger
)


class Timeline:

    def __init__(self, label="turn", clock=time.perf_counter):

        self._clock = clock

        self.label = label

        self._start = clock()

        # (stage, elapsed_seconds_since_start); first occurrence of a stage wins.
        self._marks = []

        self._seen = set()

    def mark(self, stage):

        if stage in self._seen:

            return

        self._seen.add(stage)

        self._marks.append((stage, self._clock() - self._start))

    def total_ms(self):

        if not self._marks:

            return 0.0

        return self._marks[-1][1] * 1000.0

    def deltas(self):
        """Ordered (stage, ms_since_previous_mark) pairs."""

        out = []

        prev = 0.0

        for stage, elapsed in self._marks:

            out.append((stage, (elapsed - prev) * 1000.0))

            prev = elapsed

        return out

    def summary(self):

        parts = [f"{stage}={ms:.0f}ms" for stage, ms in self.deltas()]

        return (
            f"turn[{self.label}] "
            + " ".join(parts)
            + f" total={self.total_ms():.0f}ms"
        )


_local = threading.local()


def current():

    return getattr(_local, "timeline", None)


def start_turn(label="turn", clock=time.perf_counter):

    timeline = Timeline(label, clock=clock)

    _local.timeline = timeline

    return timeline


def mark(stage):
    """Mark a stage on the current thread's timeline; no-op if none active."""

    timeline = current()

    if timeline is not None:

        timeline.mark(stage)


def end_turn():
    """Finalize the current turn: log the summary, emit a HUD metrics event, and
    clear the thread-local. Returns the Timeline, or None if no turn was active.
    Never raises — instrumentation must not break a turn."""

    timeline = current()

    if timeline is None:

        return None

    timeline.mark("done")

    try:

        logger.info(timeline.summary())

        events.emit(
            "metrics",
            summary=timeline.summary(),
            total_ms=round(timeline.total_ms(), 1),
            stages={s: round(ms, 1) for s, ms in timeline.deltas()},
        )

    except Exception:

        pass

    _local.timeline = None

    return timeline
