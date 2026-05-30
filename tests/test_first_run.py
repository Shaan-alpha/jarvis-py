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


def test_pull_model_builds_command_and_streams(monkeypatch):
    seen = {}

    class _FakeProc:
        def __init__(self):
            self.stdout = iter(["pulling 10%\n", "success\n"])
            self.returncode = 0

        def wait(self):
            return 0

    def fake_popen(cmd, **kwargs):
        seen["cmd"] = cmd
        return _FakeProc()

    monkeypatch.setattr(fr.subprocess, "Popen", fake_popen)

    lines = []
    code = fr.pull_model("phi3", on_progress=lines.append)

    assert seen["cmd"] == ["ollama", "pull", "phi3"]
    assert lines == ["pulling 10%", "success"]
    assert code == 0


def test_pull_model_handles_missing_binary(monkeypatch):
    def fake_popen(cmd, **kwargs):
        raise FileNotFoundError("ollama not found")

    monkeypatch.setattr(fr.subprocess, "Popen", fake_popen)

    msgs = []
    code = fr.pull_model("phi3", on_progress=msgs.append)

    assert code != 0
    assert any("ollama" in m.lower() for m in msgs)
