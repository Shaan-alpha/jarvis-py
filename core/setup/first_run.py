import os
import subprocess

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


def pull_model(name, on_progress=lambda line: None):
    """Run `ollama pull <name>`, streaming stripped stdout lines to a callback.

    Returns the process exit code (non-zero on failure). A missing `ollama`
    binary is reported via the callback, not raised.
    """

    try:

        proc = subprocess.Popen(
            ["ollama", "pull", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    except FileNotFoundError:

        on_progress(
            "Couldn't run 'ollama'. Install Ollama from ollama.com first."
        )

        return 1

    for line in proc.stdout:

        on_progress(line.rstrip("\n"))

    proc.stdout.close()

    return proc.wait()
