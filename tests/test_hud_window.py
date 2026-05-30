import hud.window as win


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
