import asyncio
import json
import threading
import time

# pyrefly: ignore [missing-import]
import websockets

from config.settings import (
    HUD_WS_HOST,
    HUD_WS_PORT,
    MODEL_NAME,
    MODEL_PULL_SIZE,
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


def _ready_payload():
    """The handshake each (re)connecting HUD gets: state, theme, wizard flag and
    the configured model (the wizard's pull button reads it)."""

    return {
        "type": "ready",
        "version": "1.0",
        "state": events.current_state(),
        "theme": theme_for_hour(time.localtime().tm_hour),
        "wizard": _wizard_mode,
        "model": MODEL_NAME,
        "model_size": MODEL_PULL_SIZE,
    }


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


def _read_origin(connection):
    """The connection's Origin header, or None when it cannot be read.

    `.request` exists on the ServerConnection that websockets >= 14 hands the
    handler. Older releases aliased `websockets.serve` to the legacy
    implementation, whose protocol object exposes `request_headers` instead —
    there the lookup raises, every origin reads as absent, and _origin_allowed()
    waves all of them through. requirements.txt pins the floor at 14 so this
    cannot happen; the warning is here so that if it ever does, a disabled
    Origin check announces itself instead of failing open in silence.
    """

    try:
        return connection.request.headers.get("Origin")
    except Exception as e:
        logger.warning(
            f"HUD: could not read the connection Origin ({e}); "
            f"treating it as absent. Is websockets older than 14.0?"
        )
        return None


async def _handle_client(connection):
    origin = _read_origin(connection)

    if not _origin_allowed(origin):
        logger.warning(f"HUD: rejected WS connection from origin {origin!r}")
        await connection.close(code=1008, reason="origin not allowed")
        return

    _clients.add(connection)
    logger.info("HUD client connected")

    # Send a ready handshake carrying the current state + time-of-day theme
    # so the panel re-syncs on every (re)connect, not just at process start.
    await connection.send(json.dumps(_ready_payload()))

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


def _run_server_loop():
    """Own the event loop for the server thread, and never die silently.

    Binding fails when something already holds the port — almost always a Jarvis
    that is still running. That used to surface as an unhandled exception in a
    daemon thread: the app carried on, the HUD reconnected forever against a
    socket nobody was listening on, and nothing said why."""

    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(_serve())
    except OSError as e:
        logger.error(
            f"HUD WebSocket server could not start on "
            f"{HUD_WS_HOST}:{HUD_WS_PORT} ({e}). "
            f"Is another Jarvis already running? The HUD will not connect."
        )
    except Exception:
        logger.exception("HUD WebSocket server stopped unexpectedly")


def start_in_thread():
    """Start the WebSocket server in a daemon thread with its own event loop."""

    thread = threading.Thread(target=_run_server_loop, daemon=True)
    thread.start()
