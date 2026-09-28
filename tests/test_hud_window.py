import hud.window as win


def test_api_keeps_the_window_handle_private():
    # pywebview builds the JS bridge by walking every PUBLIC attribute of js_api
    # and recursing into nested objects (webview.util.get_functions skips names
    # starting with "_"). A public reference to the pywebview Window drags that
    # walk into the native GUI object — window.native.AccessibilityObject.Bounds
    # .Empty.Empty… recurses until it blows the stack, wedging the GUI thread
    # ("Not Responding") and taking the HUD process down with it. So the window
    # handle must be underscore-prefixed.
    api = win._Api()

    exposed = [
        name for name in dir(api)
        if not name.startswith("_") and not callable(getattr(api, name))
    ]

    assert exposed == []


def test_launch_wires_the_created_window_to_the_api(monkeypatch):
    # minimize() and the close button's quit() both act on the stored handle, so
    # a rename that misses this assignment leaves both silently doing nothing.
    window = object()

    captured = {}

    def fake_create_window(title, url=None, js_api=None, **kwargs):
        captured["api"] = js_api
        return window

    monkeypatch.setattr(win.webview, "create_window", fake_create_window)
    monkeypatch.setattr(win.webview, "start", lambda *a, **k: None)

    win.launch()

    assert captured["api"]._window is window


def test_launch_builds_file_url_with_ws_fragment(monkeypatch):
    captured = {}

    def fake_create_window(title, url=None, **kwargs):
        captured["title"] = title
        captured["url"] = url

    def fake_start(*args, **kwargs):
        captured["started"] = True

    monkeypatch.setattr(win.webview, "create_window", fake_create_window)
    monkeypatch.setattr(win.webview, "start", fake_start)

    win.launch()

    # webview.start() must be called (on whatever thread the caller used).
    assert captured.get("started") is True
    assert captured["title"] == "Jarvis"
    # The WS URL rides on the fragment (#), not a query (?), so the file://
    # path stays a valid filename. The page reads it via location.hash.
    assert captured["url"].startswith("file:///")
    assert "index.html" in captured["url"]
    assert "#ws=ws://" in captured["url"]
    assert "?" not in captured["url"]
