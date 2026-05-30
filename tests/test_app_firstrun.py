import app


def test_select_mic_sets_index(monkeypatch):
    import config.settings as settings
    monkeypatch.setattr(
        app, "check_microphone",
        lambda: {"ok": True, "detail": "", "index": 3}
    )
    monkeypatch.setattr(settings, "INPUT_DEVICE_INDEX", None)
    assert app._select_mic() is True
    assert settings.INPUT_DEVICE_INDEX == 3


def test_select_mic_returns_false_when_no_mic(monkeypatch):
    monkeypatch.setattr(
        app, "check_microphone",
        lambda: {"ok": False, "detail": "No microphone found."}
    )
    assert app._select_mic() is False
