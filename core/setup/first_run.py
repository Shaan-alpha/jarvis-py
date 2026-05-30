import os

from core.memory.profile_memory import (
    PROFILE_PATH
)

from core.setup import checks


def is_first_run():
    """True when no user profile exists yet."""

    return not os.path.exists(PROFILE_PATH)


def run_checks():
    """Run all prerequisite checks; return an ordered, named list."""

    return [
        {"name": "ollama", **checks.check_ollama_running()},
        {"name": "model", **checks.check_model_present()},
        {"name": "microphone", **checks.check_microphone()},
        {"name": "webview2", **checks.check_webview2()},
    ]
