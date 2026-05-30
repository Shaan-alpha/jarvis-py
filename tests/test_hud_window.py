import hud.window as win


def test_start_in_thread_runs_launch_off_main(monkeypatch):
    started = {}

    def fake_launch():
        started["launched"] = True

    monkeypatch.setattr(win, "launch", fake_launch)

    t = win.start_in_thread()
    t.join(timeout=2)

    assert started.get("launched") is True
    assert t.daemon is True
