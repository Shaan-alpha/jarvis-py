"""Connectivity check. Stdlib + settings only, so any module can import it."""

import socket
import threading
import time

from config.settings import (
    ONLINE_CACHE_TTL,
    ONLINE_CHECK_FALLBACK_HOST,
    ONLINE_CHECK_HOST,
    ONLINE_CHECK_PORT,
    ONLINE_CHECK_TIMEOUT
)


_lock = threading.Lock()

_cache = {
    "value": None,
    "checked_at": 0.0,
}


def _probe(host, port, timeout):

    try:

        with socket.create_connection((host, port), timeout=timeout):

            return True

    except OSError:

        return False


def reset_cache():

    with _lock:

        _cache["value"] = None

        _cache["checked_at"] = 0.0


def is_online(max_age=ONLINE_CACHE_TTL):
    """True when either DNS resolver answers on :53. Cached for `max_age` s."""

    now = time.monotonic()

    with _lock:

        cached = _cache["value"]

        if cached is not None and now - _cache["checked_at"] < max_age:

            return cached

    online = any(
        _probe(host, ONLINE_CHECK_PORT, ONLINE_CHECK_TIMEOUT)
        for host in (ONLINE_CHECK_HOST, ONLINE_CHECK_FALLBACK_HOST)
    )

    with _lock:

        _cache["value"] = online

        _cache["checked_at"] = time.monotonic()

    return online
