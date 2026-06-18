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


# Tokens that mark a Bluetooth / headset HFP mic. Their hands-free profile is
# low-quality (8/16kHz, heavy processing) and openWakeWord scores it ~0, so we
# avoid them for capture even when the OS makes them the default device.
_BLUETOOTH_TOKENS = (
    "headset", "hands-free", "hands free", "handsfree", "bthhf", "bluetooth"
)


# Host-API preference, by purpose (first matching token wins). Wake word needs
# clean audio (WASAPI; MME's "communications" processing distorts speech for the
# model). STT opens mono via speech_recognition, where MME/DirectSound downmix
# cleanly and Google transcribes well, but WASAPI mono on a multi-channel device
# is unintelligible — so it's penalised.
_WAKE_HOST_SCORE = (("wasapi", 100), ("directsound", 10), ("wdm-ks", 10))

_STT_HOST_SCORE = (("mme", 100), ("directsound", 80), ("wasapi", -50), ("wdm-ks", -100))


def _host_score(host, table):

    for token, points in table:

        if token in host:

            return points

    return 0


def _device_score(device, for_wake):
    """Rank an input device for capture quality. Higher is better.

    Bluetooth/headset HFP mics are penalised heavily for both purposes (their
    hands-free audio scores ~0 for the wake word and transcribes poorly), built-in
    microphones are preferred, and the host-API preference inverts by purpose
    (see _WAKE_HOST_SCORE / _STT_HOST_SCORE).
    """

    name = (device.get("name") or "").lower()

    host = (device.get("host") or "").lower()

    score = 0

    if any(token in name for token in _BLUETOOTH_TOKENS):

        score -= 1000

    if "microphone array" in name:

        score += 20

    elif "microphone" in name:

        score += 10

    score += _host_score(host, _WAKE_HOST_SCORE if for_wake else _STT_HOST_SCORE)

    return score


def select_input_device(devices, default_index, for_wake=False):
    """Return the index of the best usable input device, or None.

    `for_wake` flips the host preference (WASAPI for the wake word, MME/
    DirectSound for STT — see _device_score). When devices carry name/host
    metadata, pick the highest-scoring real mic so the OS default being a
    Bluetooth headset doesn't sink detection. Without that metadata (e.g. unit
    tests), fall back to the OS default if input-capable, else the first input.
    """

    inputs = [d for d in devices if d.get("maxInputChannels", 0) > 0]

    if not inputs:

        return None

    has_metadata = any(("name" in d or "host" in d) for d in inputs)

    if has_metadata:

        best = max(inputs, key=lambda d: (_device_score(d, for_wake), -d["index"]))

        return best["index"]

    by_index = {d["index"]: d for d in devices}

    default = by_index.get(default_index)

    if default and default.get("maxInputChannels", 0) > 0:

        return default_index

    return inputs[0]["index"]


def check_microphone(pyaudio_module=None):
    """Probe for a usable input device. Returns a result with the chosen index."""

    if pyaudio_module is None:

        import pyaudio as pyaudio_module

    pa = pyaudio_module.PyAudio()

    try:

        devices = []

        for i in range(pa.get_device_count()):

            info = pa.get_device_info_by_index(i)

            # Attach the host-API name so select_input_device can prefer WASAPI.
            # Best-effort: a stub PyAudio (tests) may not expose host APIs.
            try:

                info = dict(info)

                info["host"] = pa.get_host_api_info_by_index(info["hostApi"])["name"]

            except Exception:

                pass

            devices.append(info)

        try:

            default_index = pa.get_default_input_device_info()["index"]

        except Exception:

            default_index = -1

    except Exception:

        return _result(False, "Microphone enumeration failed.", fixable=False)

    finally:

        pa.terminate()

    chosen = select_input_device(devices, default_index, for_wake=False)

    if chosen is None:

        return _result(False, "No microphone found.", fixable=False)

    wake = select_input_device(devices, default_index, for_wake=True)

    out = _result(True, "Microphone detected.")

    # STT device (MME/DirectSound-preferred) and wake-word device
    # (WASAPI-preferred); the same mic via different host APIs when possible.
    out["index"] = chosen

    out["wake_index"] = wake if wake is not None else chosen

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
