import asyncio
import json
import threading

# pyrefly: ignore [missing-import]
import websockets

from config.settings import (
    HUD_WS_HOST,
    HUD_WS_PORT,
)

from core.hud import events

from core.utils.logger import (
    logger,
)


_handlers = {}

_clients = set()

_loop = None


def register_handlers(**handlers):
    """Register command handlers, e.g. register_handlers(text_query=fn, wake=fn, stop=fn)."""
    _handlers.update(handlers)


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
        return handler()
    except Exception as e:
        logger.exception(f"HUD command handler error: {e}")
        return None


async def _handle_client(connection):
    _clients.add(connection)
    logger.info("HUD client connected")

    # Send a ready handshake so the panel can sync immediately.
    await connection.send(json.dumps({"type": "ready", "version": "1.0"}))

    try:
        async for raw in connection:
            _dispatch_command(raw)
    except Exception:
        pass
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

    global _loop

    def _run():
        global _loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        _loop.run_until_complete(_serve())

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
