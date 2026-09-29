import core.net as net


def _probes(monkeypatch, answers):
    calls = []

    def probe(host, port, timeout):
        calls.append(host)
        return answers.get(host, False)

    monkeypatch.setattr(net, "_probe", probe)
    net.reset_cache()
    return calls


def test_online_when_only_the_fallback_resolver_answers(monkeypatch):
    calls = _probes(monkeypatch, {"1.1.1.1": True})
    assert net.is_online() is True
    assert calls == ["8.8.8.8", "1.1.1.1"]


def test_offline_when_neither_resolver_answers(monkeypatch):
    _probes(monkeypatch, {})
    assert net.is_online() is False


def test_result_is_cached(monkeypatch):
    calls = _probes(monkeypatch, {"8.8.8.8": True})
    net.is_online()
    net.is_online()
    assert calls == ["8.8.8.8"]
