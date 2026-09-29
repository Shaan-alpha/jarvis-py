import pytest

from core.state.conversation import Conversation, is_no, is_yes, match_command


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_history_keeps_the_last_three_turns_trimmed():
    convo = Conversation()
    for i in range(5):
        convo.add_turn(f"q{i}", "x" * 500)
    history = convo.history()
    assert [u for u, _ in history] == ["q2", "q3", "q4"]
    assert all(len(r) == 200 for _, r in history)
    assert convo.last_query == "q4"
    assert convo.last_reply == "x" * 500


def test_clear_forgets_everything():
    convo = Conversation()
    convo.add_turn("q", "r")
    convo.set_results(["a"])
    convo.clear()
    assert convo.history() == [] and convo.last_reply == "" and convo.results() == []


def test_pending_action_expires():
    clock = _Clock()
    convo = Conversation(clock=clock)
    convo.set_pending("delete x", lambda: "done", ttl=30)
    assert convo.has_pending() is True
    clock.now += 31
    assert convo.has_pending() is False
    assert convo.take_pending() is None


def test_take_pending_is_one_shot():
    convo = Conversation()
    convo.set_pending("delete x", lambda: "done")
    action = convo.take_pending()
    assert action.run() == "done"
    assert convo.take_pending() is None


@pytest.mark.parametrize("query,command", [
    ("repeat that", "repeat"), ("say that again", "repeat"), ("what did you say", "repeat"),
    ("tell me more", "more"), ("go on", "more"), ("explain more", "more"),
    ("what is python", None), ("repeat after me hello", None),
])
def test_match_command(query, command):
    assert match_command(query) == command


def test_yes_and_no():
    assert is_yes("yes") and is_yes("yes please") and is_yes("go ahead")
    assert is_no("no") and is_no("cancel") and is_no("never mind")
    assert not is_yes("yesterday was fun") and not is_no("nothing else")
