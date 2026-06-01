import os

import subprocess

import webbrowser

from core.agent.registry import (
    tool
)


_APP_ALIASES = {
    "calculator": "calc",
    "calc": "calc",
    "notepad": "notepad",
    "paint": "mspaint",
    "explorer": "explorer",
    "files": "explorer",
    "cmd": "cmd",
    "command prompt": "cmd",
    "terminal": "cmd",
    "spotify": "spotify:",
    "chrome": "chrome",
    "edge": "microsoft-edge:",
    "browser": "microsoft-edge:",
}


def resolve_app(name):

    key = name.strip().lower()

    return _APP_ALIASES.get(key, key)


@tool(
    "open_app",
    "Open a Windows application by name (e.g. notepad, calculator, spotify)",
    params={
        "name": {
            "type": "str",
            "required": True,
            "desc": "the app to open, e.g. notepad",
        }
    },
)
def open_app(name):

    target = resolve_app(name)

    try:

        os.startfile(target)

    except OSError:

        # Bare app names / URI schemes (e.g. "calc", "microsoft-edge:") aren't
        # file paths, so os.startfile raises OSError; launch them via the shell
        # instead. target is derived from a user/LLM phrase and is not sanitized
        # here -- acceptable for a local single-user assistant.
        subprocess.Popen(["cmd", "/c", "start", "", target])

    return f"Opening {name}."


@tool("open_calculator", "Open Windows calculator")
def open_calculator():

    os.startfile(r"C:\Windows\System32\calc.exe")

    return "Opening calculator."


@tool("open_youtube", "Open YouTube in the browser")
def open_youtube():

    webbrowser.open("https://youtube.com")

    return "Opening YouTube."


@tool("open_google", "Open Google in the browser")
def open_google():

    webbrowser.open("https://google.com")

    return "Opening Google."


@tool("increase_volume", "Increase system volume")
def increase_volume():

    import pyautogui

    for _ in range(5):

        pyautogui.press("volumeup")

    return "Increasing volume."


@tool("decrease_volume", "Decrease system volume")
def decrease_volume():

    import pyautogui

    for _ in range(5):

        pyautogui.press("volumedown")

    return "Decreasing volume."


@tool("mute_volume", "Mute system volume")
def mute_volume():

    import pyautogui

    pyautogui.press("volumemute")

    return "Volume muted."
