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


def test_read_clipboard_long_is_truncated(monkeypatch):
    monkeypatch.setattr(agent_builtins.pyperclip, "paste", lambda: "x" * 3000)
    out = agent_builtins.read_clipboard()
    assert out.startswith("Your clipboard has")
    assert "3000 characters" in out
    assert out.endswith("(truncated).")
    # Preview is capped at the limit, not the full 3000-char blob.
    assert len(out) < 300


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
