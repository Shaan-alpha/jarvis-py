import threading

import app
import config.settings as settings
import core.speech.engine as se
import core.warmup as w


class _FakeRecognizer:
    def __init__(self, calibrated):
        self.calibrated = calibrated
        self.energy_threshold = 300
        self.calibrations = 0

    def adjust_for_ambient_noise(self, source, duration=1):
        self.calibrations += 1
        self.energy_threshold = self.calibrated


def test_the_mic_is_calibrated_once_per_wake_not_every_turn():
    se.request_calibration()
    first = _FakeRecognizer(calibrated=250)
    se._prepare_listen(first, source=None)
    assert first.calibrations == 1

    second = _FakeRecognizer(calibrated=999)
    se._prepare_listen(second, source=None)
    assert second.calibrations == 0
    assert second.energy_threshold == 250

    se.request_calibration()
    third = _FakeRecognizer(calibrated=180)
    se._prepare_listen(third, source=None)
    assert third.calibrations == 1


def test_calibration_is_capped_so_quiet_speech_is_heard():
    se.request_calibration()
    recognizer = _FakeRecognizer(calibrated=5000)
    se._prepare_listen(recognizer, source=None)
    assert recognizer.energy_threshold == settings.MAX_ENERGY_THRESHOLD


def test_end_of_speech_is_snappier_but_not_clipped():
    se.request_calibration()
    recognizer = _FakeRecognizer(calibrated=250)
    se._prepare_listen(recognizer, source=None)
    assert recognizer.pause_threshold == 0.9
    assert recognizer.non_speaking_duration <= recognizer.pause_threshold
    assert settings.STT_PHRASE_LIMIT == 8


class _Session:
    def __init__(self):
        self.activated = False

    def activate(self):
        self.activated = True


def test_wake_finishes_the_greeting_before_listening_and_warms_the_model(monkeypatch):
    calls = []
    monkeypatch.setattr(app, "stop_speaking", lambda: calls.append("stop"))
    monkeypatch.setattr(app, "prime_model", lambda: calls.append("prime"))
    monkeypatch.setattr(app, "request_calibration", lambda: calls.append("calibrate"))
    monkeypatch.setattr(app, "speak_sync", lambda text: calls.append(("say", text)))
    monkeypatch.setattr(app, "speak", lambda text: calls.append(("async", text)))
    monkeypatch.setattr(app.events, "emit", lambda *a, **k: None)
    session = _Session()
    app._on_wake(session)
    assert calls[:2] == ["stop", "prime"]
    assert ("say", "Yes Boss?") in calls
    assert ("async", "Yes Boss?") not in calls
    assert "calibrate" in calls
    assert session.activated is True


def test_hey_jarvis_while_thinking_cancels_the_answer(monkeypatch):
    cancelled = threading.Event()
    monkeypatch.setattr(app, "detect_wake_word", lambda stop_event=None, verbose=True: True)
    monkeypatch.setattr(app, "cancel_generation", cancelled.set)
    monkeypatch.setattr(app, "stop_speaking", lambda: None)
    monkeypatch.setattr(app, "clear_queue", lambda: None)

    def slow_answer(query, task_manager, raw_query=None):
        assert cancelled.wait(2), "the answer was never cancelled"

    monkeypatch.setattr(app, "process_query", slow_answer)
    app._process_with_barge_in("how are you", object(), "how are you")
    assert cancelled.is_set()


def test_the_wake_watcher_stops_when_the_answer_finishes(monkeypatch):
    seen = {}

    def detect(stop_event=None, verbose=True):
        seen["stopped"] = stop_event.wait(2)
        return False

    cancels = []
    monkeypatch.setattr(app, "detect_wake_word", detect)
    monkeypatch.setattr(app, "cancel_generation", lambda: cancels.append(1))
    monkeypatch.setattr(app, "process_query", lambda q, tm, raw_query=None: None)
    app._process_with_barge_in("hi", object(), "hi")
    assert seen["stopped"] is True
    assert cancels == []


def test_prime_model_warms_in_the_background_and_swallows_errors(monkeypatch):
    posted = []

    def fake_post(url, json=None, timeout=None):
        posted.append(json)
        raise OSError("ollama is down")

    monkeypatch.setattr(w, "_post", fake_post)
    thread = w.prime_model()
    thread.join(timeout=2)
    assert thread.daemon is True
    assert posted and posted[0]["options"]["num_predict"] == 1
    assert posted[0]["keep_alive"]


def test_going_to_sleep_forgets_the_conversation(monkeypatch):
    from core.state.conversation import conversation

    class _S:
        active = True

        def deactivate(self):
            self.active = False

    said, states = [], []
    monkeypatch.setattr(app, "stop_speaking", lambda: None)
    monkeypatch.setattr(app, "speak", said.append)
    monkeypatch.setattr(app.events, "emit", lambda evt, **kw: states.append(kw.get("state")))
    conversation.add_turn("q", "r")
    session = _S()
    app._go_to_sleep(session, "Session expired")
    assert session.active is False
    assert conversation.history() == []
    assert said == ["Going back to sleep."]
    assert states == ["idle"]
