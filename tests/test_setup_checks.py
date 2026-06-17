import core.setup.checks as checks


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_ollama_running_ok():
    def get(url, timeout=0):
        return _Resp(200, {"models": []})
    result = checks.check_ollama_running(get=get)
    assert result["ok"] is True


def test_ollama_not_running():
    def get(url, timeout=0):
        raise OSError("connection refused")
    result = checks.check_ollama_running(get=get)
    assert result["ok"] is False
    assert result["fixable"] is True


def test_model_present_true():
    payload = {"models": [{"name": "phi3:latest"}]}

    def get(url, timeout=0):
        return _Resp(200, payload)
    result = checks.check_model_present("phi3", get=get)
    assert result["ok"] is True


def test_model_present_false():
    payload = {"models": [{"name": "llama3:latest"}]}

    def get(url, timeout=0):
        return _Resp(200, payload)
    result = checks.check_model_present("phi3", get=get)
    assert result["ok"] is False
    assert result["fixable"] is True


def test_model_present_handles_unreachable():
    def get(url, timeout=0):
        raise OSError("down")
    result = checks.check_model_present("phi3", get=get)
    assert result["ok"] is False


def test_webview2_noop_off_windows():
    result = checks.check_webview2(platform="linux")
    assert result["ok"] is True


def test_webview2_present_when_reader_finds_version():
    def reader():
        return "1.0.2210.55"
    result = checks.check_webview2(platform="win32", reader=reader)
    assert result["ok"] is True


def test_webview2_missing_when_reader_returns_none():
    def reader():
        return None
    result = checks.check_webview2(platform="win32", reader=reader)
    assert result["ok"] is False
    assert result["fixable"] is True
