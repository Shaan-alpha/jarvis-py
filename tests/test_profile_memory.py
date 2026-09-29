import core.memory.profile_memory as pm


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(pm, "PROFILE_PATH", str(tmp_path / "profile.json"))


def test_likes_accumulate_without_duplicates(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    for like in ("cricket", "chess", "cricket"):
        pm.remember_profile("likes", like)
    assert pm.load_profile()["likes"] == ["chess", "cricket"]


def test_an_old_string_like_becomes_a_list(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    pm.save_profile({"likes": "robots"})
    pm.remember_profile("likes", "chess")
    assert pm.load_profile()["likes"] == ["robots", "chess"]


def test_context_renders_lists_and_readable_keys(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    pm.save_profile({"favourite_food": "biryani", "likes": ["chess", "cricket"]})
    assert pm.get_profile_context() == "favourite food: biryani\nlikes: chess, cricket"


def test_delete_profile_key(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    pm.save_profile({"city": "pune"})
    assert pm.delete_profile_key("city") is True
    assert pm.load_profile() == {}
