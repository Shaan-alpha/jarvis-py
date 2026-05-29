import core.hud.events as events


def setup_function():
    events.disable()
    events.drain(10_000)


def test_emit_is_noop_when_disabled():
    events.emit("state", state="listening")
    assert events.drain() == []


def test_emit_enqueues_event_with_type_and_ts():
    events.enable()
    events.emit("state", state="listening")
    drained = events.drain()
    assert len(drained) == 1
    event = drained[0]
    assert event["type"] == "state"
    assert event["state"] == "listening"
    assert "ts" in event


def test_drain_empties_the_bus():
    events.enable()
    events.emit("a")
    events.emit("b")
    assert len(events.drain()) == 2
    assert events.drain() == []


def test_current_state_tracks_latest_state_event():
    # current_state() feeds the WS `ready` handshake so a reconnecting HUD
    # re-syncs; it must reflect the most recent "state" event.
    events.enable()
    events.emit("state", state="thinking")
    assert events.current_state() == "thinking"
    events.emit("state", state="speaking")
    assert events.current_state() == "speaking"
