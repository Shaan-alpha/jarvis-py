import app


class _FakeTaskManager:
    def __init__(self):
        self.reminders = []

    def add_reminder_in_minutes(self, minutes, message):
        self.reminders.append((minutes, message))


def test_sets_reminder(monkeypatch):
    spoken = []
    monkeypatch.setattr(app, "speak", lambda t: spoken.append(t))
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    tm = _FakeTaskManager()
    app.process_query("remind me in 5 minutes to drink water", tm)
    assert tm.reminders == [(5, "drink water")]
    assert any("Reminder set" in s for s in spoken)


def test_routes_to_intent_handler(monkeypatch):
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    monkeypatch.setattr(app, "parse_reminder", lambda q: None)
    called = {}

    def fake_handler(query, speak):
        called["q"] = query

    fake_handler.__name__ = "handle_media_control"
    monkeypatch.setattr(app, "route_intent", lambda q: fake_handler)
    monkeypatch.setattr(app, "speak", lambda t: None)
    app.process_query("volume up", _FakeTaskManager())
    assert called["q"] == "volume up"


def test_llm_fallback_saves_memory(monkeypatch):
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    monkeypatch.setattr(app, "parse_reminder", lambda q: None)
    monkeypatch.setattr(app, "route_intent", lambda q: None)
    monkeypatch.setattr(app, "decide_tool", lambda q: None)
    monkeypatch.setattr(app, "ask_llm", lambda q: "an answer")
    saved = {}
    monkeypatch.setattr(app, "save_memory", lambda q, r: saved.setdefault("v", (q, r)))
    monkeypatch.setattr(app, "speak", lambda t: None)
    app.process_query("what is python", _FakeTaskManager())
    assert saved["v"] == ("what is python", "an answer")
