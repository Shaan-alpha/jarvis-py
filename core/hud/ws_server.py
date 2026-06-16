import asyncio
import json
import threading
import time

# pyrefly: ignore [missing-import]
import websockets

from config.settings import (
    HUD_WS_HOST,
    HUD_WS_PORT,
)

from core.hud import events

from core.hud.theming import (
    theme_for_hour,
)

from core.utils.logger import (
    logger,
)


_handlers = {}

_clients = set()

_wizard_mode = False


def register_handlers(**handlers):
    """Register command handlers, e.g. register_handlers(text_query=fn, wake=fn, stop=fn)."""
    _handlers.update(handlers)


def set_wizard_mode(enabled):
    """Mark whether the first-run wizard should open when a client connects.

    Carried in the `ready` handshake (rather than a one-shot broadcast) so a
    slow-starting HUD that connects after the event is emitted still opens the
    wizard."""
    global _wizard_mode
    _wizard_mode = bool(enabled)


def _origin_allowed(origin):
    """True unless `origin` is an explicit remote web origin.

    The HUD loads from file:// (pywebview), which sends ``Origin: null`` or no
    Origin at all, so null/absent/file: are allowed. We reject http(s):// so a
    web page you visit while Jarvis runs can't connect to ws://127.0.0.1 and
    drive commands (open/close apps, write files) — the classic local-WebSocket
    / DNS-rebinding surface.
    """

    if not origin:

        return True

    normalized = origin.strip().lower()

    if normalized in ("null", ""):

        return True

    if normalized.startswith("file:"):

        return True

    return not normalized.startswith(("http://", "https://"))


def _dispatch_command(raw):
    """Parse one raw command string and invoke the matching handler. Returns
    the handler's result, or None when ignored. Pure + unit-testable."""

    try:
        message = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("HUD: received non-JSON command")
        return None

    command = message.get("type")
    handler = _handlers.get(command)

    if handler is None:
        logger.info(f"HUD: no handler for command {command!r}")
        return None

    try:

        if command == "text_query":

            return handler(message.get("text", ""))

        if command == "save_name":

            return handler(message.get("name", ""))

        if command == "pull_model":

            return handler(message.get("model", ""))

        return handler()

    except Exception as e:

        logger.exception(f"HUD command handler error: {e}")

        return None


async def _handle_client(connection):
    try:
        origin = connection.request.headers.get("Origin")
    except Exception:
        origin = None

    if not _origin_allowed(origin):
        logger.warning(f"HUD: rejected WS connection from origin {origin!r}")
        await connection.close(code=1008, reason="origin not allowed")
        return

    _clients.add(connection)
    logger.info("HUD client connected")

    # Send a ready handshake carrying the current state + time-of-day theme
    # so the panel re-syncs on every (re)connect, not just at process start.
    await connection.send(json.dumps({
        "type": "ready",
        "version": "1.0",
        "state": events.current_state(),
        "theme": theme_for_hour(time.localtime().tm_hour),
        "wizard": _wizard_mode,
    }))

    try:
        async for raw in connection:
            _dispatch_command(raw)
    except Exception:
        logger.debug("HUD client loop ended", exc_info=True)
    finally:
        _clients.discard(connection)
        logger.info("HUD client disconnected")


async def _broadcaster():
    while True:
        for event in events.drain():
            if _clients:
                data = json.dumps(event)
                for client in list(_clients):
                    try:
                        await client.send(data)
                    except Exception:
                        _clients.discard(client)
        await asyncio.sleep(0.03)


async def _serve():
    async with websockets.serve(_handle_client, HUD_WS_HOST, HUD_WS_PORT):
        logger.info(f"HUD WebSocket server on ws://{HUD_WS_HOST}:{HUD_WS_PORT}")
        await _broadcaster()


def start_in_thread():
    """Start the WebSocket server in a daemon thread with its own event loop."""

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_serve())

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
