import core.agent.web_tools as web


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise web.requests.HTTPError(str(self.status_code))


def _route(monkeypatch, table, online=True):
    calls = []

    def get(url, params=None, timeout=None, headers=None):
        calls.append(url)
        for key, payload in table.items():
            if key in url:
                return _Resp(payload)
        return _Resp({}, 404)

    monkeypatch.setattr(web.requests, "get", get)
    monkeypatch.setattr(web, "is_online", lambda: online)
    return calls


_TURING = {
    "w/api.php": ["alan turing", ["Alan Turing"], [""], ["https://en.wikipedia.org/wiki/Alan_Turing"]],
    "page/summary/Alan_Turing": {
        "type": "standard",
        "extract": "Alan Turing was an English mathematician. He was a pioneer of computing. He was born in 1912.",
    },
}


def test_lookup_speaks_the_start_of_the_wikipedia_summary(monkeypatch):
    _route(monkeypatch, _TURING)
    assert web.lookup("Alan Turing") == \
        "According to Wikipedia, Alan Turing was an English mathematician. He was a pioneer of computing."


def test_disambiguation_falls_back_to_duckduckgo(monkeypatch):
    _route(monkeypatch, {
        "w/api.php": ["mercury", ["Mercury"], [""], [""]],
        "page/summary/Mercury": {"type": "disambiguation", "extract": "Mercury may refer to:"},
        "api.duckduckgo.com": {"AbstractText": "Mercury is the smallest planet.", "Answer": ""},
    })
    assert web.lookup("mercury") == "Mercury is the smallest planet."


def test_answers_are_cached_and_reused_offline(monkeypatch):
    calls = _route(monkeypatch, _TURING)
    first = web.lookup("Alan Turing")
    monkeypatch.setattr(web, "is_online", lambda: False)
    assert web.lookup("alan turing") == first
    assert len(calls) == 2


def test_offline_with_nothing_cached_makes_no_request(monkeypatch):
    calls = _route(monkeypatch, _TURING, online=False)
    assert web.lookup("Alan Turing") is None
    assert calls == []


def test_lookups_can_be_switched_off(monkeypatch):
    calls = _route(monkeypatch, _TURING)
    monkeypatch.setattr(web, "ONLINE_LOOKUPS", False)
    assert web.lookup("Alan Turing") is None
    assert calls == []


def test_a_network_error_returns_none(monkeypatch):
    def boom(*a, **k):
        raise web.requests.ConnectionError("down")
    monkeypatch.setattr(web.requests, "get", boom)
    monkeypatch.setattr(web, "is_online", lambda: True)
    assert web.lookup("anything") is None


def test_a_corrupt_cache_is_ignored(monkeypatch):
    with open(web.CACHE_PATH, "w", encoding="utf-8") as handle:
        handle.write("[not a dict")
    _route(monkeypatch, _TURING)
    assert web.lookup("Alan Turing").startswith("According to Wikipedia")


def test_first_sentences_caps_words():
    text = "One two three four five six. Seven eight."
    assert web.first_sentences(text, max_words=4) == "One two three four…"
