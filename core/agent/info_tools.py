"""Deterministic answers for what a language model cannot know: the clock,
battery, memory, disk, uptime and connectivity. Router-only (llm=False)."""

import os
import sys
import time

from datetime import datetime

import psutil

from core.agent.registry import (
    tool
)

from core.net import (
    is_online
)

from core.text import (
    plural,
    spoken_date,
    spoken_time
)


def _clock():

    return datetime.now()


def _epoch():

    return time.time()


def _system_drive():

    if sys.platform == "win32":

        return os.environ.get("SystemDrive", "C:") + "\\"

    return "/"


def _gb(num_bytes):
    """'3.4 GB' / '120 GB'."""

    text = f"{num_bytes / 2 ** 30:.1f}".rstrip("0").rstrip(".")

    return f"{text} GB"


def _duration(seconds):

    days, minutes = divmod(int(seconds // 60), 1440)

    hours, minutes = divmod(minutes, 60)

    parts = []

    if days:

        parts.append(plural(days, "day"))

    if hours:

        parts.append(plural(hours, "hour"))

    if minutes and not days:

        parts.append(plural(minutes, "minute"))

    return " ".join(parts) or "less than a minute"


@tool("get_time", "Tell the current local time", llm=False)
def get_time():

    return f"It's {spoken_time(_clock())}."


@tool("get_date", "Tell today's date", llm=False)
def get_date():

    return f"It's {spoken_date(_clock())}."


@tool("get_day", "Tell the day of the week", llm=False)
def get_day():

    return f"It's {_clock().strftime('%A')}."


@tool("battery_status", "Report the battery level", llm=False)
def battery_status():

    battery = psutil.sensors_battery()

    if battery is None:

        return "This PC doesn't report a battery."

    charging = "charging" if battery.power_plugged else "on battery"

    return f"Battery is at {battery.percent:.0f} percent, {charging}."


@tool("memory_usage", "Report RAM usage", llm=False)
def memory_usage():

    memory = psutil.virtual_memory()

    return f"Memory is {memory.percent:.0f} percent used, {_gb(memory.available)} free."


@tool("disk_space", "Report free space on the system drive", llm=False)
def disk_space():

    drive = _system_drive()

    usage = psutil.disk_usage(drive)

    label = drive.rstrip(":\\/") or "root"

    return f"Drive {label} has {_gb(usage.free)} free of {_gb(usage.total)}."


@tool("uptime", "Report how long the PC has been on", llm=False)
def uptime():

    return f"Your PC has been on for {_duration(_epoch() - psutil.boot_time())}."


@tool("network_status", "Report whether the internet is reachable", llm=False)
def network_status():

    return "You're online." if is_online() else "You're offline."
