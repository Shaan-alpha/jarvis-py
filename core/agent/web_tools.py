"""Answers from free, keyless web sources — Wikipedia, DuckDuckGo Instant
Answer, Open-Meteo — with a local cache so a repeated question still works
offline. Router-only (llm=False). Nothing here is required: every miss or
failure returns something honest or falls back to the local model.
"""

import os
import re
import threading
import time
import urllib.parse

import requests

from config.settings import (
    ONLINE_LOOKUPS,
    WEB_TIMEOUT
)

from core.agent.registry import (
    Reply,
    tool
)

from core.net import (
    is_online
)

from core.paths import user_data_dir

from core.text import normalize

from core.utils.jsonio import (
    read_json,
    write_json_atomic,
)


CACHE_PATH = os.path.join(str(user_data_dir()), "data", "cache", "web.json")

LOOKUP_TTL = 30 * 24 * 3600

WEATHER_TTL = 30 * 60

CACHE_MAX_ENTRIES = 500

MAX_ANSWER_WORDS = 40

USER_AGENT = "JarvisPy/3.6 (local voice assistant; https://github.com/Shaan-alpha/jarvis-py)"

_WIKI_SEARCH = "https://en.wikipedia.org/w/api.php"

_WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"

_DDG = "https://api.duckduckgo.com/"

_cache_lock = threading.Lock()


def _now():

    return time.time()


def _read_cache():

    data = read_json(CACHE_PATH, default={})

    return data if isinstance(data, dict) else {}


def _cache_get(key, ttl, allow_stale=False):

    entry = _read_cache().get(key)

    if not isinstance(entry, dict) or "value" not in entry:

        return None

    if allow_stale or _now() - entry.get("at", 0) <= ttl:

        return entry["value"]

    return None


def _cache_put(key, value):

    with _cache_lock:

        data = _read_cache()

        data[key] = {"at": _now(), "value": value}

        if len(data) > CACHE_MAX_ENTRIES:

            for old in sorted(data, key=lambda k: data[k].get("at", 0))[:len(data) - CACHE_MAX_ENTRIES]:

                data.pop(old)

        write_json_atomic(CACHE_PATH, data)


def _get_json(url, params=None):

    response = requests.get(
        url,
        params=params,
        timeout=WEB_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )

    response.raise_for_status()

    return response.json()


def first_sentences(text, max_sentences=2, max_words=MAX_ANSWER_WORDS):
    """The first sentence or two, capped at `max_words` — a spoken answer."""

    sentences = re.split(r"(?<=[.!?])\s+", (text or "").strip())

    answer = " ".join(sentences[:max_sentences])

    words = answer.split()

    if len(words) > max_words:

        answer = " ".join(words[:max_words]).rstrip(",;:") + "…"

    return answer


# Returned by _wikipedia when the best match is a disambiguation page: the
# topic has several meanings, so Jarvis asks instead of guessing one.
_AMBIGUOUS = object()


def _spoken(text, prefix=""):
    """Speak one sentence; show up to three."""

    return {
        "say": prefix + first_sentences(text, max_sentences=1, max_words=35),
        "show": prefix + first_sentences(text, max_sentences=3, max_words=90),
    }


_FILLER_WORDS = {"the", "and", "for", "with", "about", "what", "who", "how", "are", "was", "were"}


def _tokens(text):

    return {word for word in normalize(text).split() if len(word) >= 3 and word not in _FILLER_WORDS}


def _relevant(topic, title):
    """Relevance search returns *some* article for almost any text, so the top
    title must share a real word with the question (prefix match allows
    plurals: "tower" / "towers"). Too little to judge -> accept."""

    wanted, got = _tokens(topic), _tokens(title)

    if not wanted:

        return True

    return any(
        a == b or (min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)))
        for a in wanted for b in got
    )


def _wikipedia(topic):
    """Relevance search, not opensearch: opensearch answers "Python" with the
    disambiguation page, relevance search with the programming language."""

    hits = _get_json(_WIKI_SEARCH, {
        "action": "query", "list": "search", "srsearch": topic, "srlimit": 3, "format": "json",
    })

    titles = [hit["title"] for hit in hits.get("query", {}).get("search", [])]

    if not titles or not _relevant(topic, titles[0]):

        return None

    summary = _get_json(_WIKI_SUMMARY + urllib.parse.quote(titles[0].replace(" ", "_"), safe=""))

    if summary.get("type") == "disambiguation":

        return _AMBIGUOUS

    extract = (summary.get("extract") or "").strip()

    return _spoken(extract, "According to Wikipedia, ") if extract else None


def _duckduckgo(topic):

    data = _get_json(_DDG, {"q": topic, "format": "json", "no_html": 1, "skip_disambig": 1})

    text = data.get("AbstractText") or data.get("Answer") or data.get("Definition") or ""

    return _spoken(text) if text.strip() else None


def _as_reply(cached):
    """A cached answer as a Reply (older cache entries were plain text)."""

    if isinstance(cached, dict):

        return Reply(**cached)

    return Reply(say=cached, show=cached)


@tool(
    "lookup",
    "Look up a person, place or thing online",
    params={"topic": {"type": "str", "required": True, "desc": "what to look up"}},
    llm=False,
)
def lookup(topic):

    topic = (topic or "").strip(" ?.!")

    if not topic:

        return None

    key = "lookup:" + topic.lower()

    cached = _cache_get(key, LOOKUP_TTL)

    if cached:

        return _as_reply(cached)

    if not ONLINE_LOOKUPS or not is_online():

        # A stale answer beats a guess; with none, the LLM answers (grounded).
        stale = _cache_get(key, LOOKUP_TTL, allow_stale=True)

        return _as_reply(stale) if stale else None

    for fetch in (_wikipedia, _duckduckgo):

        try:

            answer = fetch(topic)

        except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):

            answer = None

        if answer is _AMBIGUOUS:

            # DuckDuckGo would just pick one meaning; ask instead of guessing.
            return f"{topic} can mean several things. Which one do you mean?"

        if answer:

            _cache_put(key, answer)

            return Reply(**answer)

    return None


_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"

_FORECAST = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes -> words.
_WMO = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "foggy", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    56: "freezing drizzle", 57: "freezing drizzle", 61: "light rain", 63: "rain",
    65: "heavy rain", 66: "freezing rain", 67: "freezing rain", 71: "light snow",
    73: "snow", 75: "heavy snow", 77: "snow grains", 80: "light showers",
    81: "showers", 82: "heavy showers", 85: "snow showers", 86: "snow showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail",
}


def _profile_city():

    from core.memory.profile_memory import load_profile

    return load_profile().get("city")


def _describe_weather(name, data):

    current, daily = data["current"], data["daily"]

    temp = round(current["temperature_2m"])

    sky = _WMO.get(current.get("weather_code"), "")

    high = round(daily["temperature_2m_max"][0])

    low = round(daily["temperature_2m_min"][0])

    rain = (daily.get("precipitation_probability_max") or [None])[0]

    say = f"In {name} it's {temp} degrees" + (f" and {sky}" if sky else "") + f"; high {high}, low {low}"

    show = f"{name}: {temp}°C" + (f", {sky}" if sky else "") + f" · high {high}° / low {low}°"

    if rain is not None:

        say += f", {round(rain)} percent chance of rain"

        show += f" · rain {round(rain)}%"

    return {"say": say + ".", "show": show}


@tool(
    "weather",
    "Current weather and today's forecast",
    params={"city": {"type": "str", "required": False, "desc": "city name; defaults to where the user lives"}},
    llm=False,
)
def weather(city=None):

    place = (city or "").strip() or _profile_city()

    if not place:

        return "Which city? Say 'weather in' and the city."

    key = "weather:" + place.lower()

    cached = _cache_get(key, WEATHER_TTL)

    if cached:

        return Reply(**cached)

    if not ONLINE_LOOKUPS or not is_online():

        stale = _cache_get(key, WEATHER_TTL, allow_stale=True)

        if stale:

            return Reply(say=f"I'm offline. Last I checked: {stale['say']}", show=stale["show"])

        return "I'm offline, so I can't check the weather."

    try:

        results = _get_json(_GEOCODE, {"name": place, "count": 1, "language": "en", "format": "json"}).get("results")

        if not results:

            return f"I couldn't find a place called {place}."

        location = results[0]

        data = _get_json(_FORECAST, {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current": "temperature_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": 1,
        })

        report = _describe_weather(location.get("name", place), data)

    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):

        return "I couldn't reach the weather service."

    _cache_put(key, report)

    return Reply(**report)
