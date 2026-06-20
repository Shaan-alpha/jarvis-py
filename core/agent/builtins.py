import os

import subprocess

import urllib.parse

import webbrowser

import psutil

import pyperclip

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


# Win11 Calculator is a UWP app: launching calc.exe spawns CalculatorApp.exe and
# the calc.exe stub exits immediately, so `taskkill /im calc.exe` finds nothing to
# kill. Target the real process image instead.
_CLOSE_IMAGES = {
    "calculator": "CalculatorApp.exe",
    "calc": "CalculatorApp.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
}


def resolve_close_image(name):

    key = name.strip().lower()

    if key in _CLOSE_IMAGES:

        return _CLOSE_IMAGES[key]

    return key if key.endswith(".exe") else f"{key}.exe"


@tool(
    "close_app",
    "Close a running Windows application by name (e.g. notepad, calculator, paint)",
    params={
        "name": {
            "type": "str",
            "required": True,
            "desc": "the app to close, e.g. notepad",
        }
    },
)
def close_app(name):

    image = resolve_close_image(name)

    # subprocess.run (not os.system) per the audit's hardening note; check=False
    # so "no such process" never raises (target may already be closed).
    subprocess.run(
        ["taskkill", "/f", "/im", image],
        check=False,
        capture_output=True,
    )

    return f"Closing {name}."


@tool("system_status", "Report CPU usage and battery status")
def system_status():

    cpu = psutil.cpu_percent(interval=0.3)

    battery = psutil.sensors_battery()

    if battery is None:

        return f"CPU at {cpu:.0f} percent."

    pct = battery.percent

    charging = "charging" if battery.power_plugged else "on battery"

    return (
        f"CPU at {cpu:.0f} percent, "
        f"battery {pct:.0f} percent, {charging}."
    )


@tool(
    "search_web",
    "Search the web for a query in the browser",
    params={
        "query": {
            "type": "str",
            "required": True,
            "desc": "what to search for, e.g. weather today",
        }
    },
)
def search_web(query):

    url = (
        "https://www.google.com/search?q="
        + urllib.parse.quote_plus(query)
    )

    webbrowser.open(url)

    return f"Searching the web for {query}."


CLIPBOARD_PREVIEW_LIMIT = 200


@tool("read_clipboard", "Read the current text contents of the system clipboard")
def read_clipboard():

    text = pyperclip.paste()

    if not text or not text.strip():

        return "The clipboard is empty."

    if len(text) <= CLIPBOARD_PREVIEW_LIMIT:

        return text

    return (
        f"Your clipboard has {len(text)} characters. "
        f'It starts: "{text[:CLIPBOARD_PREVIEW_LIMIT]}..." (truncated).'
    )


@tool(
    "write_clipboard",
    "Copy the given text to the system clipboard",
    params={
        "text": {
            "type": "str",
            "required": True,
            "desc": "the text to copy to the clipboard",
        }
    },
)
def write_clipboard(text):

    pyperclip.copy(text)

    return "Copied to clipboard."
