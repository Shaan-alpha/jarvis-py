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
    tool
)

from core.net import (
    is_online
)

from core.paths import user_data_dir

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


def _wikipedia(topic):

    hits = _get_json(_WIKI_SEARCH, {
        "action": "opensearch", "search": topic, "limit": 1, "namespace": 0, "format": "json",
    })

    titles = hits[1] if isinstance(hits, list) and len(hits) > 1 else []

    if not titles:

        return None

    summary = _get_json(_WIKI_SUMMARY + urllib.parse.quote(titles[0].replace(" ", "_"), safe=""))

    if summary.get("type") == "disambiguation":

        return None

    extract = (summary.get("extract") or "").strip()

    return f"According to Wikipedia, {first_sentences(extract)}" if extract else None


def _duckduckgo(topic):

    data = _get_json(_DDG, {"q": topic, "format": "json", "no_html": 1, "skip_disambig": 1})

    text = data.get("AbstractText") or data.get("Answer") or data.get("Definition") or ""

    return first_sentences(text) if text.strip() else None


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

        return cached

    if not ONLINE_LOOKUPS or not is_online():

        # A stale answer beats a guess; with none, the LLM answers (grounded).
        return _cache_get(key, LOOKUP_TTL, allow_stale=True)

    for fetch in (_wikipedia, _duckduckgo):

        try:

            answer = fetch(topic)

        except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):

            answer = None

        if answer:

            _cache_put(key, answer)

            return answer

    return None
