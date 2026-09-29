from datetime import datetime
from types import SimpleNamespace

import core.agent.info_tools as info


def _at(monkeypatch, moment):
    monkeypatch.setattr(info, "_clock", lambda: moment)


def test_time_is_short_with_no_leading_zero(monkeypatch):
    _at(monkeypatch, datetime(2026, 9, 28, 16, 5))
    assert info.get_time() == "It's 4:05 PM."


def test_morning_time(monkeypatch):
    _at(monkeypatch, datetime(2026, 9, 28, 9, 30))
    assert info.get_time() == "It's 9:30 AM."


def test_date(monkeypatch):
    _at(monkeypatch, datetime(2026, 9, 28, 16, 5))
    assert info.get_date() == "It's Monday, 28 September 2026."


def test_day(monkeypatch):
    _at(monkeypatch, datetime(2026, 9, 28, 16, 5))
    assert info.get_day() == "It's Monday."


def test_battery_charging(monkeypatch):
    monkeypatch.setattr(info.psutil, "sensors_battery",
                        lambda: SimpleNamespace(percent=96.4, power_plugged=True))
    assert info.battery_status() == "Battery is at 96 percent, charging."


def test_battery_on_battery(monkeypatch):
    monkeypatch.setattr(info.psutil, "sensors_battery",
                        lambda: SimpleNamespace(percent=41.0, power_plugged=False))
    assert info.battery_status() == "Battery is at 41 percent, on battery."


def test_no_battery(monkeypatch):
    monkeypatch.setattr(info.psutil, "sensors_battery", lambda: None)
    assert info.battery_status() == "This PC doesn't report a battery."


def test_memory_usage(monkeypatch):
    monkeypatch.setattr(info.psutil, "virtual_memory",
                        lambda: SimpleNamespace(percent=78.2, available=3.4 * 2 ** 30))
    assert info.memory_usage() == "Memory is 78 percent used, 3.4 GB free."


def test_disk_space(monkeypatch):
    monkeypatch.setattr(info, "_system_drive", lambda: "C:\\")
    monkeypatch.setattr(info.psutil, "disk_usage",
                        lambda path: SimpleNamespace(free=120 * 2 ** 30, total=476 * 2 ** 30))
    assert info.disk_space() == "Drive C has 120 GB free of 476 GB."


def test_uptime(monkeypatch):
    monkeypatch.setattr(info.psutil, "boot_time", lambda: 1000.0)
    monkeypatch.setattr(info, "_epoch", lambda: 1000.0 + 3 * 3600 + 12 * 60)
    assert info.uptime() == "Your PC has been on for 3 hours 12 minutes."


def test_network_status(monkeypatch):
    monkeypatch.setattr(info, "is_online", lambda: True)
    assert info.network_status() == "You're online."
    monkeypatch.setattr(info, "is_online", lambda: False)
    assert info.network_status() == "You're offline."
