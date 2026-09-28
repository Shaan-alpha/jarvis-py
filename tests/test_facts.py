import numpy as np
import pytest

import core.memory.facts as facts

_VOCAB = ["exam", "fifth", "car", "blue", "mom", "birthday", "june", "keys", "drawer", "wifi", "password"]


def _encode(texts):
    vectors = []
    for text in texts:
        words = text.lower().split()
        vector = np.array([1.0 if w in words else 0.0 for w in _VOCAB] + [0.05], dtype=np.float32)
        vectors.append(vector / np.linalg.norm(vector))
    return vectors


@pytest.fixture(autouse=True)
def _fake_encoder(monkeypatch):
    monkeypatch.setattr(facts, "encode", _encode)


def test_a_remembered_fact_is_found_by_meaning():
    facts.add_fact("my exam is on the fifth")
    facts.add_fact("my car is blue")
    assert facts.search_facts("when is my exam") == ["my exam is on the fifth"]


def test_unrelated_questions_find_nothing():
    facts.add_fact("my car is blue")
    assert facts.search_facts("wifi password") == []


def test_a_near_duplicate_updates_instead_of_piling_up():
    facts.add_fact("my exam is on the fifth")
    facts.add_fact("the exam is on the fifth")
    stored = facts.all_facts()
    assert len(stored) == 1
    assert stored[0]["text"] == "the exam is on the fifth"


def test_facts_survive_a_restart():
    facts.add_fact("my keys are in the drawer")
    facts.reset_cache()
    assert facts.search_facts("where are my keys") == ["my keys are in the drawer"]


def test_the_store_is_capped_dropping_the_least_recently_used(monkeypatch):
    ticks = iter(range(100))
    monkeypatch.setattr(facts, "_now", lambda: next(ticks))
    monkeypatch.setattr(facts, "MAX_FACTS", 2)
    facts.add_fact("my exam is on the fifth")
    facts.add_fact("my car is blue")
    facts.add_fact("mom birthday is in june")
    texts = [f["text"] for f in facts.all_facts()]
    assert texts == ["my car is blue", "mom birthday is in june"]


def test_find_and_delete_a_fact():
    facts.add_fact("my car is blue")
    hit = facts.find_fact("my car")
    assert hit["text"] == "my car is blue"
    assert facts.delete_fact(hit["id"]) is True
    assert facts.all_facts() == []


def test_an_empty_store_never_loads_the_embedder(monkeypatch):
    def boom(texts):
        raise AssertionError("encoded with nothing stored")
    monkeypatch.setattr(facts, "encode", boom)
    assert facts.search_facts("anything") == []
    assert facts.find_fact("anything") is None


def test_a_corrupt_file_reads_as_empty():
    with open(facts.FACTS_PATH, "w", encoding="utf-8") as handle:
        handle.write("{not json")
    assert facts.search_facts("anything") == []
    facts.add_fact("my car is blue")
    assert len(facts.all_facts()) == 1


def test_clear_facts():
    facts.add_fact("my car is blue")
    facts.clear_facts()
    assert facts.all_facts() == []
