import pytest

import core.agent.memory_tools as mt
from core.agent.registry import Reply
from core.state.conversation import conversation


class _FakeFacts:
    def __init__(self):
        self.items = []

    def add_fact(self, text):
        self.items.append({"id": str(len(self.items)), "text": text, "created": len(self.items)})

    def all_facts(self):
        return list(self.items)

    def find_fact(self, query):
        return next((f for f in self.items if query in f["text"]), None)

    def delete_fact(self, fact_id):
        self.items = [f for f in self.items if f["id"] != fact_id]
        return True

    def clear_facts(self):
        self.items = []


@pytest.fixture
def store(monkeypatch):
    fake, profile = _FakeFacts(), {}
    monkeypatch.setattr(mt, "facts", fake)
    monkeypatch.setattr(mt, "load_profile", lambda: dict(profile))

    def delete_key(key):
        return profile.pop(key, None) is not None

    monkeypatch.setattr(mt, "delete_profile_key", delete_key)
    return fake, profile


def test_remember_says_got_it_and_stores(store):
    fake, _ = store
    assert mt.remember_fact("My exam is on the 5th.") == Reply(say="Got it.", show="Remembered: My exam is on the 5th")
    assert fake.items[0]["text"] == "My exam is on the 5th"


def test_recall_speaks_three_items_in_second_person(store):
    fake, profile = store
    profile["name"] = "shaan"
    for text in ("my exam is on the 5th", "my car is blue", "i live near the station"):
        fake.add_fact(text)
    out = mt.recall_memory()
    assert out.say == "I remember: your name is shaan; you live near the station; your car is blue."
    assert "your exam is on the 5th" in out.show


def test_recall_with_nothing_saved(store):
    assert mt.recall_memory().startswith("I don't have anything saved")


def test_profile_value_accepts_the_old_spelling(store):
    _, profile = store
    profile["favorite_language"] = "python"
    assert mt.get_profile_value("favourite language") == "Your favourite language is python."
    assert mt.get_profile_value("city") == "You haven't told me your city yet."


def test_forget_asks_first_then_deletes_on_confirmation(store):
    fake, _ = store
    fake.add_fact("my car is blue")
    out = mt.forget_memory("car")
    assert "Say yes to confirm" in out.say
    assert fake.items
    assert conversation.take_pending().run() == "Forgotten."
    assert fake.items == []


def test_forget_a_profile_detail_speaks_a_sentence_even_if_already_gone(store):
    _, profile = store
    profile["city"] = "pune"
    assert mt.forget_memory("city") == "Forget your city? Say yes to confirm."
    profile.clear()
    assert conversation.take_pending().run() == "Forgotten your city."


def test_forget_everything_needs_confirmation(store):
    fake, _ = store
    fake.add_fact("my car is blue")
    assert "Say yes" in mt.forget_memory("everything")
    assert fake.items


def test_forget_unknown(store):
    assert mt.forget_memory("dragons") == "I don't have anything saved about dragons."


def test_second_person():
    assert mt.second_person("my exam is on the 5th") == "your exam is on the 5th"
    assert mt.second_person("i am tired and im hungry") == "you are tired and youre hungry"
