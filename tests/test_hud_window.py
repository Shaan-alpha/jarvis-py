from types import SimpleNamespace

import hud.window as win


class _Event:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self


class _FakeWindow:
    def __init__(self):
        self.events = SimpleNamespace(shown=_Event())


def _launch(monkeypatch):
    captured = {}
    window = _FakeWindow()

    def fake_create_window(title, url=None, js_api=None, **kwargs):
        captured.update(title=title, url=url, api=js_api, kwargs=kwargs)
        return window

    monkeypatch.setattr(win.webview, "create_window", fake_create_window)
    monkeypatch.setattr(win.webview, "start", lambda *a, **k: captured.setdefault("started", True))
    win.launch()
    return captured, window


def test_api_keeps_the_window_handle_private():
    # pywebview walks every PUBLIC js_api attribute recursively; a public Window
    # reference recursed into the native .NET object until the stack blew.
    api = win._Api()
    exposed = [n for n in dir(api) if not n.startswith("_") and not callable(getattr(api, n))]
    assert exposed == []


def test_launch_wires_the_created_window_to_the_api(monkeypatch):
    captured, window = _launch(monkeypatch)
    assert captured["api"]._window is window


def test_launch_builds_file_url_with_ws_and_theme_fragment(monkeypatch):
    captured, _ = _launch(monkeypatch)
    assert captured.get("started") is True
    assert captured["title"] == "Jarvis"
    assert captured["url"].startswith("file:///")
    assert "#ws=ws://" in captured["url"]
    assert "&theme=" in captured["url"]
    assert "?" not in captured["url"]


def test_window_is_compact_draggable_by_title_bar_and_selectable(monkeypatch):
    captured, window = _launch(monkeypatch)
    kwargs = captured["kwargs"]
    assert (kwargs["width"], kwargs["height"]) == (380, 360)
    assert kwargs["easy_drag"] is False
    assert kwargs["text_select"] is True
    assert kwargs["frameless"] is True
    assert window.events.shown.handlers


class _FakeDwm:
    def __init__(self):
        self.calls = []

    def DwmSetWindowAttribute(self, hwnd, attribute, value, size):
        self.calls.append((hwnd, attribute, size))
        return 0


def test_native_frame_rounds_corners_and_sets_the_outline():
    dwm = _FakeDwm()
    assert win.apply_native_frame(1234, dwm=dwm) is True
    assert [call[1] for call in dwm.calls] == [33, 34]


def test_native_frame_failure_is_harmless():
    class _Broken:
        def DwmSetWindowAttribute(self, *args):
            raise OSError("no DWM here")

    assert win.apply_native_frame(1, dwm=_Broken()) is False
