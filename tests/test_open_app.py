from core.agent import builtins as agent_builtins
from core.agent import registry


def test_resolve_app_alias():
    assert agent_builtins.resolve_app("Calculator") == "calc"


def test_resolve_app_passthrough():
    assert agent_builtins.resolve_app("vlc") == "vlc"


def test_open_app_calls_startfile(monkeypatch):
    calls = []
    monkeypatch.setattr(agent_builtins.os, "startfile",
                        lambda target: calls.append(target), raising=False)
    out = agent_builtins.open_app("calculator")
    assert calls == ["calc"]
    assert out == "Opening calculator."


def test_open_app_falls_back_to_subprocess(monkeypatch):
    def _raise(target):
        raise OSError("not a file")

    popen_calls = []
    monkeypatch.setattr(agent_builtins.os, "startfile", _raise, raising=False)
    monkeypatch.setattr(agent_builtins.subprocess, "Popen",
                        lambda args: popen_calls.append(args))
    out = agent_builtins.open_app("notepad")
    assert popen_calls == [["cmd", "/c", "start", "", "notepad"]]
    assert out == "Opening notepad."


def test_builtins_registered():
    from core.agent import loader
    loader.load_builtins()
    for name in ("open_app", "open_calculator", "open_youtube", "open_google",
                 "increase_volume", "decrease_volume", "mute_volume"):
        assert registry.get(name) is not None
