from core.agent import builtins as agent_builtins
from core.agent import registry


# --- close_app -------------------------------------------------------------

def test_resolve_close_image_known():
    # Win11 Calculator runs as the UWP process CalculatorApp.exe; calc.exe is
    # only a launcher stub that exits immediately, so taskkilling it is a no-op.
    assert agent_builtins.resolve_close_image("Calculator") == "CalculatorApp.exe"
    assert agent_builtins.resolve_close_image("calc") == "CalculatorApp.exe"
    assert agent_builtins.resolve_close_image("notepad") == "notepad.exe"
    assert agent_builtins.resolve_close_image("paint") == "mspaint.exe"


def test_resolve_close_image_passthrough():
    assert agent_builtins.resolve_close_image("vlc") == "vlc.exe"
    assert agent_builtins.resolve_close_image("foo.exe") == "foo.exe"


def test_close_app_runs_taskkill(monkeypatch):
    calls = []

    def _fake_run(cmd, check=True, **kwargs):
        calls.append((cmd, check, kwargs.get("capture_output")))

    monkeypatch.setattr(agent_builtins.subprocess, "run", _fake_run)
    out = agent_builtins.close_app("notepad")
    assert calls == [(["taskkill", "/f", "/im", "notepad.exe"], False, True)]
    assert out == "Closing notepad."


# --- system_status ---------------------------------------------------------

def test_system_status_with_battery(monkeypatch):
    class _Batt:
        percent = 80
        power_plugged = True

    monkeypatch.setattr(agent_builtins.psutil, "cpu_percent",
                        lambda interval=0: 42.0)
    monkeypatch.setattr(agent_builtins.psutil, "sensors_battery",
                        lambda: _Batt())
    out = agent_builtins.system_status()
    assert out == "CPU at 42 percent, battery 80 percent, charging."


def test_system_status_no_battery(monkeypatch):
    monkeypatch.setattr(agent_builtins.psutil, "cpu_percent",
                        lambda interval=0: 42.0)
    monkeypatch.setattr(agent_builtins.psutil, "sensors_battery",
                        lambda: None)
    out = agent_builtins.system_status()
    assert out == "CPU at 42 percent."


# --- search_web ------------------------------------------------------------

def test_search_web_opens_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(agent_builtins.webbrowser, "open",
                        lambda url: opened.append(url))
    out = agent_builtins.search_web("funny cats")
    assert opened == ["https://www.google.com/search?q=funny+cats"]
    assert out == "Searching the web for funny cats."


# --- registration ----------------------------------------------------------

def test_new_tools_registered():
    from core.agent import loader
    loader.load_builtins()
    for name in ("close_app", "system_status", "search_web"):
        assert registry.get(name) is not None
