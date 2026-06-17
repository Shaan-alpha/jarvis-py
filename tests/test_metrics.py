import threading

import core.utils.metrics as m
from core.utils.metrics import Timeline


class _FakeClock:
    """Returns a preset sequence of timestamps, one per call."""

    def __init__(self, times):
        self._times = list(times)
        self._i = 0

    def __call__(self):
        t = self._times[self._i]
        self._i += 1
        return t


def test_timeline_records_marks_and_deltas():
    clock = _FakeClock([0.0, 0.010, 0.050, 0.060])
    tl = Timeline("text", clock=clock)
    tl.mark("routed")        # 0.010 -> 10ms since start
    tl.mark("first_token")   # 0.050 -> 40ms since prev
    tl.mark("first_audio")   # 0.060 -> 10ms since prev
    deltas = dict(tl.deltas())
    assert round(deltas["routed"]) == 10
    assert round(deltas["first_token"]) == 40
    assert round(deltas["first_audio"]) == 10
    assert round(tl.total_ms()) == 60


def test_timeline_dedupes_repeated_stage():
    clock = _FakeClock([0.0, 0.010])   # dup mark must not consume a timestamp
    tl = Timeline(clock=clock)
    tl.mark("first_token")
    tl.mark("first_token")             # ignored; first occurrence wins
    assert [s for s, _ in tl.deltas()] == ["first_token"]


def test_summary_has_label_stages_and_total():
    clock = _FakeClock([0.0, 0.010, 0.060])
    tl = Timeline("text", clock=clock)
    tl.mark("routed")
    tl.mark("done")
    s = tl.summary()
    assert s.startswith("turn[text]")
    assert "routed=10ms" in s
    assert "total=60ms" in s


def test_mark_is_noop_without_active_turn():
    m.end_turn()          # clear any stray turn on this thread
    m.mark("whatever")    # must not raise
    assert m.current() is None


def test_start_mark_end_roundtrip(monkeypatch):
    emitted = {}
    monkeypatch.setattr(m.events, "emit",
                        lambda evt, **kw: emitted.setdefault(evt, kw))
    clock = _FakeClock([0.0, 0.010, 0.060])
    tl = m.start_turn("voice", clock=clock)
    m.mark("routed")
    out = m.end_turn()
    assert out is tl
    assert "metrics" in emitted
    assert emitted["metrics"]["total_ms"] >= 0
    assert m.current() is None


def test_thread_local_isolation():
    m.start_turn("main")
    seen = {}

    def worker():
        seen["current"] = m.current()      # fresh thread -> no active turn
        m.start_turn("worker")
        seen["worker_label"] = m.current().label
        m.end_turn()

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    assert seen["current"] is None
    assert seen["worker_label"] == "worker"
    assert m.current().label == "main"     # main's timeline untouched
    m.end_turn()
