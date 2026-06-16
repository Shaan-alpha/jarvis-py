"""Crash-safe JSON persistence helpers.

`write_json_atomic` serializes to a temp file in the same directory and then
`os.replace()`s it over the target, so a crash/power-loss mid-write can leave a
stray `.tmp` file but never a half-written (and unloadable) target. `read_json`
tolerates a missing or corrupt file by returning a caller-supplied default.

Stdlib-only by design (no project imports) so any module can use it.
"""

import json
import os
import tempfile


def read_json(path, default=None):
    """Load JSON from `path`; return `default` if missing or corrupt."""

    if not os.path.exists(path):

        return default

    try:

        with open(path, "r", encoding="utf-8") as file:

            return json.load(file)

    except (json.JSONDecodeError, OSError, ValueError):

        return default


def write_json_atomic(path, data, indent=4):
    """Write `data` to `path` as JSON atomically (temp file + os.replace)."""

    directory = os.path.dirname(path) or "."

    os.makedirs(directory, exist_ok=True)

    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")

    try:

        with os.fdopen(fd, "w", encoding="utf-8") as file:

            json.dump(data, file, indent=indent)

        os.replace(tmp, path)

    except BaseException:

        # Don't leave a partial temp file behind if serialization failed.
        try:

            os.remove(tmp)

        except OSError:

            pass

        raise
