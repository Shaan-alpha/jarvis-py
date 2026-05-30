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


def select_input_device(devices, default_index):
    """Return the index of a usable input device, or None.

    Prefer the OS default if it can capture; else the first input-capable
    device; else None.
    """

    by_index = {d["index"]: d for d in devices}

    default = by_index.get(default_index)

    if default and default.get("maxInputChannels", 0) > 0:

        return default_index

    for device in devices:

        if device.get("maxInputChannels", 0) > 0:

            return device["index"]

    return None


def check_microphone(pyaudio_module=None):
    """Probe for a usable input device. Returns a result with the chosen index."""

    if pyaudio_module is None:

        import pyaudio as pyaudio_module

    pa = pyaudio_module.PyAudio()

    try:

        devices = [
            pa.get_device_info_by_index(i)
            for i in range(pa.get_device_count())
        ]

        try:

            default_index = pa.get_default_input_device_info()["index"]

        except Exception:

            default_index = -1

    except Exception:

        return _result(False, "Microphone enumeration failed.", fixable=False)

    finally:

        pa.terminate()

    chosen = select_input_device(devices, default_index)

    if chosen is None:

        return _result(False, "No microphone found.", fixable=False)

    out = _result(True, "Microphone detected.")

    out["index"] = chosen

    return out


def _read_webview2_version():
    """Best-effort read of the installed WebView2 runtime version (Windows)."""

    try:

        import winreg

    except ImportError:

        return None

    key_path = (
        r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients"
        r"\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    )

    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):

        try:

            with winreg.OpenKey(hive, key_path) as key:

                value, _ = winreg.QueryValueEx(key, "pv")

                if value:

                    return value

        except OSError:

            continue

    return None


def check_webview2(platform=sys.platform, reader=_read_webview2_version):
    """On Windows, confirm the WebView2 runtime is installed. No-op elsewhere."""

    if platform != "win32":

        return _result(True, "WebView2 not required on this platform.")

    version = reader()

    if version:

        return _result(True, f"WebView2 runtime {version} installed.")

    return _result(
        False,
        "WebView2 runtime missing. Install it from Microsoft's Evergreen page.",
        fixable=True
    )
