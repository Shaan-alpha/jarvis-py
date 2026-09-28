import pytest

import app

from core.agent.registry import ToolCall


@pytest.mark.parametrize("query,ends_session", [
    ("bye", True),
    ("goodbye", True),
    ("ok bye", True),
    ("exit", True),
    ("shutdown", True),
    ("stop listening", True),
    # A bare substring test ended the session on ordinary speech that merely
    # contains an exit word, so Jarvis went quiet mid-conversation.
    ("i exited the app", False),
    ("the exits are marked", False),
    ("shutdowns are scheduled monthly", False),
])
def test_exit_command_matches_whole_words_only(query, ends_session):
    assert app.is_exit_command(query) is ends_session


class _FakeTaskManager:
    def __init__(self):
        self.reminders = []

    def add_reminder_in_minutes(self, minutes, message):
        self.reminders.append((minutes, message))


def test_sets_reminder(monkeypatch):
    responded = []
    monkeypatch.setattr(app, "respond", lambda v: responded.append(v))
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    tm = _FakeTaskManager()
    app.process_query("remind me in 5 minutes to drink water", tm)
    assert tm.reminders == [(5, "drink water")]
    assert responded == ["Reminder set for 5 minutes."]


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
    responded = []
    monkeypatch.setattr(app, "respond", lambda v: responded.append(v))

    app.process_query("volume up", _FakeTaskManager())
    assert ran["call"] == ToolCall("increase_volume", {})
    assert responded == ["Increasing volume."]


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
    monkeypatch.setattr(app, "respond", lambda v: None)

    app.process_query("open spotify", _FakeTaskManager())
    assert ran["call"] == ToolCall("open_app", {"name": "spotify"})


def test_llm_turns_are_not_saved_to_long_term_memory(monkeypatch):
    from core.memory import facts
    _quiet_routing(monkeypatch)
    monkeypatch.setattr(app, "ask_llm", lambda q: "an answer")
    app.process_query("what is python", _FakeTaskManager())
    assert facts.all_facts() == []
    assert not hasattr(app, "save_memory")


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
    monkeypatch.setattr(app, "respond", lambda v: None)

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
    monkeypatch.setattr(app, "respond", lambda v: None)

    app.process_query("volume up", _FakeTaskManager())

    assert "metrics" in captured
    stages = captured["metrics"]["stages"]
    assert "routed" in stages and "done" in stages
    assert metrics.current() is None      # turn cleaned up even on the tool path


def test_shutdown_handler_stops_services_then_exits(monkeypatch):
    calls = []
    monkeypatch.setattr(app, "stop_speaking", lambda: calls.append("stop_speaking"))
    monkeypatch.setattr(app, "clear_queue", lambda: calls.append("clear_queue"))
    monkeypatch.setattr(app, "stop_tts_queue", lambda: calls.append("stop_tts_queue"))

    class _TM:
        def stop(self):
            calls.append("tm.stop")

    exited = {}

    def _fake_exit(code):
        exited["code"] = code
        raise SystemExit(code)     # halt like os._exit would, but testably

    monkeypatch.setattr(app.os, "_exit", _fake_exit)

    with pytest.raises(SystemExit):
        app._hud_on_shutdown(_TM())

    assert exited["code"] == 0
    # Services stopped (mic released) before the process exits.
    assert {"stop_speaking", "stop_tts_queue", "tm.stop"} <= set(calls)


def test_pull_model_always_pulls_the_configured_model(monkeypatch):
    pulled = []
    monkeypatch.setattr(app, "_spawn", lambda target, *a, **k: target(*a, **k))
    monkeypatch.setattr(app, "pull_model", lambda name, on_progress=None: pulled.append(name))
    monkeypatch.setattr(app.events, "emit", lambda *a, **k: None)
    app._hud_on_pull_model("something-else")
    assert pulled == [app.settings.MODEL_NAME]


def test_save_name_closes_wizard_mode(monkeypatch):
    import core.hud.ws_server as ws_mod
    ws_mod.set_wizard_mode(True)
    monkeypatch.setattr(app, "update_profile", lambda k, v: None)
    monkeypatch.setattr(app.events, "emit", lambda *a, **k: None)
    app._hud_on_save_name("Tony")
    assert ws_mod._wizard_mode is False


from core.state.conversation import conversation


def _quiet_routing(monkeypatch):
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    monkeypatch.setattr(app, "parse_reminder", lambda q: None)
    monkeypatch.setattr(app, "resolve_keyword_tool", lambda q, raw=None: None)
    monkeypatch.setattr(app, "decide_tool", lambda q, raw=None: None)


def test_repeat_that_replays_the_last_reply(monkeypatch):
    _quiet_routing(monkeypatch)
    conversation.add_turn("what is python", "A programming language.")
    responded = []
    monkeypatch.setattr(app, "respond", lambda v: responded.append(v))
    app.process_query("repeat that", _FakeTaskManager())
    assert responded == ["A programming language."]


def test_tell_me_more_reasks_the_last_question_in_detail(monkeypatch):
    _quiet_routing(monkeypatch)
    conversation.add_turn("who is alan turing", "A mathematician.")
    asked = {}

    def fake_ask(q, detailed=False):
        asked.update(q=q, detailed=detailed)
        return "More."

    monkeypatch.setattr(app, "ask_llm", fake_ask)
    app.process_query("tell me more", _FakeTaskManager())
    assert asked == {"q": "who is alan turing", "detailed": True}


def test_llm_turns_are_remembered_for_follow_ups(monkeypatch):
    _quiet_routing(monkeypatch)
    monkeypatch.setattr(app, "ask_llm", lambda q: "Lima.")
    app.process_query("capital of peru", _FakeTaskManager(), raw_query="Capital of Peru?")
    assert conversation.history() == [("Capital of Peru?", "Lima.")]


def test_yes_runs_the_pending_action(monkeypatch):
    ran, responded = [], []
    conversation.set_pending("do it", lambda: ran.append(1) or "Done.")
    monkeypatch.setattr(app, "respond", lambda v: responded.append(v) or None)
    app.process_query("yes", _FakeTaskManager())
    assert ran == [1] and responded == ["Done."]


def test_no_cancels_the_pending_action(monkeypatch):
    ran, responded = [], []
    conversation.set_pending("do it", lambda: ran.append(1))
    monkeypatch.setattr(app, "respond", lambda v: responded.append(v) or None)
    app.process_query("cancel", _FakeTaskManager())
    assert ran == [] and responded == ["Cancelled."]


def test_another_command_lets_the_confirmation_lapse(monkeypatch):
    ran = []
    conversation.set_pending("do it", lambda: ran.append(1))
    _quiet_routing(monkeypatch)
    monkeypatch.setattr(app, "ask_llm", lambda q: "")
    app.process_query("what is python", _FakeTaskManager())
    app.process_query("yes", _FakeTaskManager())
    assert ran == []
