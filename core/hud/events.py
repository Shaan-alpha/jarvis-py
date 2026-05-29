import queue
import time


_enabled = False

_bus = queue.Queue(maxsize=1000)

# Last known voice state, tracked even while disabled so a HUD that
# (re)connects can be told the current state in the `ready` handshake.
_current_state = "idle"


def enable():
    global _enabled
    _enabled = True


def disable():
    global _enabled
    _enabled = False


def is_enabled():
    return _enabled


def current_state():
    return _current_state


def emit(event_type, **payload):
    """Publish an event to the HUD bus. No-op (and zero cost) when disabled."""

    global _current_state

    if event_type == "state":
        _current_state = payload.get("state", _current_state)

    if not _enabled:
        return

    event = {"type": event_type, "ts": time.time()}
    event.update(payload)

    try:
        _bus.put_nowait(event)
    except queue.Full:
        # Lossy by design: if the HUD has stalled, drop rather than block
        # the voice loop.
        pass


def drain(max_items=200):
    """Pop up to `max_items` events from the bus (used by the WS broadcaster)."""

    items = []

    for _ in range(max_items):

        try:
            items.append(_bus.get_nowait())
        except queue.Empty:
            break

    return items
