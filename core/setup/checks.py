import sys

import requests

from config.settings import (
    MODEL_NAME,
    OLLAMA_TAGS_URL
)


def _result(ok, detail, fixable=False):

    return {"ok": ok, "detail": detail, "fixable": fixable}


def check_ollama_running(get=requests.get):
    """True when the Ollama HTTP API answers on localhost."""

    try:

        resp = get(OLLAMA_TAGS_URL, timeout=2)

    except Exception:

        return _result(
            False,
            "Ollama isn't reachable. Install it from ollama.com and start it.",
            fixable=True
        )

    if resp.status_code == 200:

        return _result(True, "Ollama is running.")

    return _result(
        False,
        f"Ollama returned HTTP {resp.status_code}.",
        fixable=True
    )


def check_model_present(name=MODEL_NAME, get=requests.get):
    """True when an Ollama model whose tag starts with `name` is installed."""

    try:

        resp = get(OLLAMA_TAGS_URL, timeout=2)

        models = resp.json().get("models", [])

    except Exception:

        return _result(
            False,
            "Couldn't list Ollama models (is Ollama running?).",
            fixable=True
        )

    for model in models:

        tag = model.get("name", "")

        if tag == name or tag.startswith(f"{name}:"):

            return _result(True, f"Model '{name}' is installed.")

    return _result(
        False,
        f"Model '{name}' isn't pulled yet.",
        fixable=True
    )
