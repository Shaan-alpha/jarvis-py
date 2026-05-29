import threading
import time

import psutil

from config.settings import (
    HUD_STATS_INTERVAL,
    MODEL_NAME,
)

from core.hud import events

from core.hud.theming import (
    theme_for_hour,
)

from core.speech.engine import (
    is_online,
)


_running = False


def build_stats_payload():
    """Snapshot CPU/battery/model/connectivity for the HUD status row."""

    cpu = psutil.cpu_percent(interval=None)

    battery = psutil.sensors_battery()

    if battery is None:
        battery_pct = None
        charging = None
    else:
        battery_pct = battery.percent
        charging = battery.power_plugged

    return {
        "cpu": cpu,
        "battery_pct": battery_pct,
        "charging": charging,
        "model": MODEL_NAME,
        "online": is_online(),
    }


def _loop():
    last_theme = None

    while _running:

        events.emit("stats", **build_stats_payload())

        theme = theme_for_hour(time.localtime().tm_hour)

        if theme != last_theme:
            events.emit("theme", theme=theme)
            last_theme = theme

        time.sleep(HUD_STATS_INTERVAL)


def start():
    global _running

    if _running:
        return

    _running = True

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()


def stop():
    global _running
    _running = False
