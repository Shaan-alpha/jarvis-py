from core.agent import builtins as agent_builtins
from core.agent import registry


def test_read_clipboard_empty(monkeypatch):
    monkeypatch.setattr(agent_builtins.pyperclip, "paste", lambda: "")
    assert agent_builtins.read_clipboard() == "The clipboard is empty."


def test_read_clipboard_whitespace(monkeypatch):
    monkeypatch.setattr(agent_builtins.pyperclip, "paste", lambda: "   ")
    assert agent_builtins.read_clipboard() == "The clipboard is empty."


def test_read_clipboard_short_returns_verbatim(monkeypatch):
    monkeypatch.setattr(agent_builtins.pyperclip, "paste", lambda: "hello")
    assert agent_builtins.read_clipboard() == "hello"


def test_read_clipboard_long_speaks_a_preview_and_shows_more(monkeypatch):
    from core.agent.registry import Reply
    monkeypatch.setattr(agent_builtins.pyperclip, "paste", lambda: "x" * 3000)
    out = agent_builtins.read_clipboard()
    assert isinstance(out, Reply)
    assert out.say.startswith("Your clipboard has 3000 characters.")
    assert len(out.say) < 180
    assert out.show == "x" * 2000


def test_write_clipboard_copies_and_confirms(monkeypatch):
    copied = []
    monkeypatch.setattr(agent_builtins.pyperclip, "copy",
                        lambda t: copied.append(t))
    out = agent_builtins.write_clipboard("remember the milk")
    assert copied == ["remember the milk"]
    assert out == "Copied to clipboard."


def test_clipboard_tools_registered():
    from core.agent import loader
    loader.load_builtins()
    for name in ("read_clipboard", "write_clipboard"):
        assert registry.get(name) is not None
