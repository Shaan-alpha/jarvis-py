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


def _search(*titles):
    return {"query": {"search": [{"title": t} for t in titles]}}


_TURING = {
    "w/api.php": _search("Alan Turing", "Turing Award"),
    "page/summary/Alan_Turing": {
        "type": "standard",
        "extract": "Alan Turing was an English mathematician. He was a pioneer of computing. He was born in 1912.",
    },
}


def test_lookup_speaks_one_sentence_and_shows_more(monkeypatch):
    _route(monkeypatch, _TURING)
    out = web.lookup("Alan Turing")
    assert out.say == "According to Wikipedia, Alan Turing was an English mathematician."
    assert out.show.endswith("He was born in 1912.")


def test_an_ambiguous_word_takes_the_most_relevant_article(monkeypatch):
    # Opensearch answered "Python" with the disambiguation page, and the old
    # fallback read out a Cold War plan. Relevance search ranks the article.
    _route(monkeypatch, {
        "w/api.php": _search("Python (programming language)", "Monty Python", "Python"),
        "page/summary/Python_%28programming_language%29": {
            "type": "standard", "extract": "Python is a high-level programming language. It is popular.",
        },
    })
    assert web.lookup("Python").say == "According to Wikipedia, Python is a high-level programming language."


def test_a_genuinely_ambiguous_topic_asks_which_instead_of_guessing(monkeypatch):
    calls = _route(monkeypatch, {
        "w/api.php": _search("Mercury", "Freddie Mercury", "Mercury (element)"),
        "page/summary/Mercury": {"type": "disambiguation", "extract": "Mercury may refer to:"},
        "api.duckduckgo.com": {"AbstractText": "Mercury is the smallest planet.", "Answer": ""},
    })
    assert web.lookup("mercury") == "mercury can mean several things. Which one do you mean?"
    assert not any("duckduckgo" in url for url in calls)


def test_duckduckgo_answers_when_wikipedia_has_nothing(monkeypatch):
    _route(monkeypatch, {
        "w/api.php": _search(),
        "api.duckduckgo.com": {"AbstractText": "A zorbonk is a made-up word. Nobody uses it.", "Answer": ""},
    })
    assert web.lookup("zorbonk").say == "A zorbonk is a made-up word."


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
    assert web.lookup("Alan Turing").say.startswith("According to Wikipedia")


def test_an_old_plain_text_cache_entry_still_works(monkeypatch):
    calls = _route(monkeypatch, _TURING, online=False)
    web._cache_put("lookup:alan turing", "According to Wikipedia, an older cached answer.")
    assert web.lookup("Alan Turing").say == "According to Wikipedia, an older cached answer."
    assert calls == []


def test_first_sentences_caps_words():
    text = "One two three four five six. Seven eight."
    assert web.first_sentences(text, max_words=4) == "One two three four…"


from core.agent.registry import Reply

_PUNE = {
    "geocoding-api.open-meteo.com": {"results": [{"name": "Pune", "latitude": 18.5, "longitude": 73.9}]},
    "api.open-meteo.com/v1/forecast": {
        "current": {"temperature_2m": 27.4, "weather_code": 2},
        "daily": {"temperature_2m_max": [31.2], "temperature_2m_min": [21.8],
                  "precipitation_probability_max": [40]},
    },
}


def test_weather_for_a_named_city(monkeypatch):
    _route(monkeypatch, _PUNE)
    out = web.weather("pune")
    assert out == Reply(
        say="In Pune it's 27 degrees and partly cloudy; high 31, low 22, 40 percent chance of rain.",
        show="Pune: 27°C, partly cloudy · high 31° / low 22° · rain 40%",
    )


def test_weather_defaults_to_the_profile_city(monkeypatch):
    _route(monkeypatch, _PUNE)
    monkeypatch.setattr(web, "_profile_city", lambda: "pune")
    assert web.weather().say.startswith("In Pune")


def test_weather_without_a_city_asks_which(monkeypatch):
    _route(monkeypatch, _PUNE)
    monkeypatch.setattr(web, "_profile_city", lambda: None)
    assert web.weather() == "Which city? Say 'weather in' and the city."


def test_weather_offline_uses_the_last_report(monkeypatch):
    _route(monkeypatch, _PUNE)
    web.weather("pune")
    monkeypatch.setattr(web, "is_online", lambda: False)
    monkeypatch.setattr(web, "_now", lambda: 10 ** 12)
    out = web.weather("pune")
    assert out.say.startswith("I'm offline. Last I checked: In Pune")


def test_weather_offline_with_nothing_saved(monkeypatch):
    calls = _route(monkeypatch, _PUNE, online=False)
    assert web.weather("pune") == "I'm offline, so I can't check the weather."
    assert calls == []


def test_weather_unknown_place(monkeypatch):
    _route(monkeypatch, {"geocoding-api.open-meteo.com": {"results": []}})
    assert web.weather("atlantis") == "I couldn't find a place called atlantis."


def test_an_unrelated_top_article_is_not_read_out(monkeypatch):
    _route(monkeypatch, {
        "w/api.php": _search("Zebra"),
        "page/summary/Zebra": {"type": "standard", "extract": "Zebras are African equines."},
        "api.duckduckgo.com": {"AbstractText": "", "Answer": ""},
    })
    assert web.lookup("zorbonk") is None
