import core.hud.stats as stats


def test_build_stats_payload_with_battery(monkeypatch):
    monkeypatch.setattr(stats.psutil, "cpu_percent", lambda interval=None: 23.0)

    class _Bat:
        percent = 88
        power_plugged = True

    monkeypatch.setattr(stats.psutil, "sensors_battery", lambda: _Bat())
    monkeypatch.setattr(stats, "is_online", lambda: True)

    payload = stats.build_stats_payload()
    assert payload["cpu"] == 23.0
    assert payload["battery_pct"] == 88
    assert payload["charging"] is True
    assert payload["online"] is True
    assert "model" in payload


def test_build_stats_payload_without_battery(monkeypatch):
    monkeypatch.setattr(stats.psutil, "cpu_percent", lambda interval=None: 10.0)
    monkeypatch.setattr(stats.psutil, "sensors_battery", lambda: None)
    monkeypatch.setattr(stats, "is_online", lambda: False)

    payload = stats.build_stats_payload()
    assert payload["battery_pct"] is None
    assert payload["charging"] is None
    assert payload["online"] is False
