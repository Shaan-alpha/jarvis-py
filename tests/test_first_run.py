import core.setup.first_run as fr


def test_is_first_run_true_when_profile_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(fr, "PROFILE_PATH", str(tmp_path / "nope.json"))
    assert fr.is_first_run() is True


def test_is_first_run_false_when_profile_exists(monkeypatch, tmp_path):
    profile = tmp_path / "user_profile.json"
    profile.write_text("{}")
    monkeypatch.setattr(fr, "PROFILE_PATH", str(profile))
    assert fr.is_first_run() is False


def test_run_checks_returns_named_results(monkeypatch):
    monkeypatch.setattr(fr.checks, "check_ollama_running", lambda: {"ok": True, "detail": "", "fixable": False})
    monkeypatch.setattr(fr.checks, "check_model_present", lambda: {"ok": False, "detail": "", "fixable": True})
    monkeypatch.setattr(fr.checks, "check_microphone", lambda: {"ok": True, "detail": "", "index": 1})
    monkeypatch.setattr(fr.checks, "check_webview2", lambda: {"ok": True, "detail": ""})
    results = fr.run_checks()
    names = [r["name"] for r in results]
    assert names == ["ollama", "model", "microphone", "webview2"]
