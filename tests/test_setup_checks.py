import core.setup.checks as checks


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_ollama_running_ok():
    get = lambda url, timeout=0: _Resp(200, {"models": []})
    result = checks.check_ollama_running(get=get)
    assert result["ok"] is True


def test_ollama_not_running():
    def get(url, timeout=0):
        raise OSError("connection refused")
    result = checks.check_ollama_running(get=get)
    assert result["ok"] is False
    assert result["fixable"] is True
