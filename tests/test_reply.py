import core.speech.reply as reply
import core.speech.tts_queue as tq
from core.agent.registry import Reply


def _capture(monkeypatch):
    emitted, queued = [], []
    monkeypatch.setattr(reply.events, "emit", lambda evt, **kw: emitted.append((evt, kw)))
    monkeypatch.setattr(reply, "add_to_queue", queued.append)
    return emitted, queued


def test_respond_speaks_and_shows_a_plain_string(monkeypatch):
    emitted, queued = _capture(monkeypatch)
    reply.respond("Opening notepad.")
    assert queued == ["Opening notepad."]
    assert emitted == [("assistant_done", {"full_text": "Opening notepad."})]


def test_respond_speaks_short_but_shows_full(monkeypatch):
    emitted, queued = _capture(monkeypatch)
    reply.respond(Reply(say="Found 3 files.", show="a.txt\nb.txt\nc.txt"))
    assert queued == ["Found 3 files."]
    assert emitted == [("assistant_done", {"full_text": "a.txt\nb.txt\nc.txt"})]


def test_respond_ignores_nothing_to_say(monkeypatch):
    emitted, queued = _capture(monkeypatch)
    assert reply.respond(None) is None
    assert reply.respond("") is None
    assert emitted == [] and queued == []


def test_announce_reminder_toasts_and_queues(monkeypatch):
    emitted, queued = _capture(monkeypatch)
    reply.announce_reminder("drink water")
    assert emitted == [("reminder_fired", {"message": "drink water"})]
    assert queued == ["Reminder. drink water"]


def test_tts_worker_reports_speaking_then_idle(monkeypatch):
    states = []
    monkeypatch.setattr(tq.events, "emit", lambda evt, **kw: states.append(kw.get("state")))
    monkeypatch.setattr(tq, "speak_sync", lambda text: None)
    tq.clear_queue()
    tq.tts_queue.put("hello")
    tq.tts_queue.get()
    tq._play("hello")
    assert states == ["speaking", "idle"]
