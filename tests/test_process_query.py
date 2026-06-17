import app

from core.agent.registry import ToolCall


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


def test_fast_path_resolves_and_executes_tool(monkeypatch):
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    monkeypatch.setattr(app, "parse_reminder", lambda q: None)
    monkeypatch.setattr(app, "resolve_keyword_tool",
                        lambda q, raw=None: ToolCall("increase_volume", {}))

    # The LLM path must NOT run on a keyword hit.
    def _boom(q, raw=None):
        raise AssertionError("decide_tool should not run on a keyword hit")

    monkeypatch.setattr(app, "decide_tool", _boom)

    ran = {}

    def _fake_execute(call):
        ran["call"] = call
        return "Increasing volume."

    monkeypatch.setattr(app, "execute_tool", _fake_execute)
    spoken = []
    monkeypatch.setattr(app, "speak", lambda t: spoken.append(t))

    app.process_query("volume up", _FakeTaskManager())
    assert ran["call"] == ToolCall("increase_volume", {})
    assert spoken == ["Increasing volume."]


def test_keyword_miss_falls_through_to_llm_tool_agent(monkeypatch):
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    monkeypatch.setattr(app, "parse_reminder", lambda q: None)
    monkeypatch.setattr(app, "resolve_keyword_tool", lambda q, raw=None: None)
    monkeypatch.setattr(app, "decide_tool",
                        lambda q, raw=None: ToolCall("open_app", {"name": "spotify"}))

    ran = {}

    def _fake_execute(call):
        ran["call"] = call
        return "Opening spotify."

    monkeypatch.setattr(app, "execute_tool", _fake_execute)
    monkeypatch.setattr(app, "speak", lambda t: None)

    app.process_query("open spotify", _FakeTaskManager())
    assert ran["call"] == ToolCall("open_app", {"name": "spotify"})


def test_llm_fallback_saves_memory(monkeypatch):
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    monkeypatch.setattr(app, "parse_reminder", lambda q: None)
    monkeypatch.setattr(app, "resolve_keyword_tool", lambda q, raw=None: None)
    monkeypatch.setattr(app, "decide_tool", lambda q, raw=None: None)
    monkeypatch.setattr(app, "ask_llm", lambda q: "an answer")
    saved = {}
    monkeypatch.setattr(app, "save_memory", lambda q, r: saved.setdefault("v", (q, r)))
    monkeypatch.setattr(app, "speak", lambda t: None)
    app.process_query("what is python", _FakeTaskManager())
    assert saved["v"] == ("what is python", "an answer")


def test_raw_query_preserves_case_for_routers(monkeypatch):
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    monkeypatch.setattr(app, "parse_reminder", lambda q: None)

    seen = {}

    def _resolve(q, raw=None):
        seen["resolve"] = (q, raw)
        return None

    def _decide(q, raw=None):
        seen["decide"] = (q, raw)
        return None

    monkeypatch.setattr(app, "resolve_keyword_tool", _resolve)
    monkeypatch.setattr(app, "decide_tool", _decide)
    monkeypatch.setattr(app, "ask_llm", lambda q: "")
    monkeypatch.setattr(app, "speak", lambda t: None)

    app.process_query("copy hello world to clipboard", _FakeTaskManager(),
                      raw_query="copy Hello World to clipboard")

    assert seen["resolve"] == ("copy hello world to clipboard",
                               "copy Hello World to clipboard")
    assert seen["decide"] == ("copy hello world to clipboard",
                              "copy Hello World to clipboard")


def test_process_query_records_latency_metrics(monkeypatch):
    import core.utils.metrics as metrics

    captured = {}

    def _capture(evt, **kw):
        if evt == "metrics":
            captured["metrics"] = kw

    monkeypatch.setattr(metrics.events, "emit", _capture)
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    monkeypatch.setattr(app, "parse_reminder", lambda q: None)
    monkeypatch.setattr(app, "resolve_keyword_tool",
                        lambda q, raw=None: ToolCall("increase_volume", {}))
    monkeypatch.setattr(app, "decide_tool", lambda q, raw=None: None)
    monkeypatch.setattr(app, "execute_tool", lambda c: "ok")
    monkeypatch.setattr(app, "speak", lambda t: None)

    app.process_query("volume up", _FakeTaskManager())

    assert "metrics" in captured
    stages = captured["metrics"]["stages"]
    assert "routed" in stages and "done" in stages
    assert metrics.current() is None      # turn cleaned up even on the tool path
