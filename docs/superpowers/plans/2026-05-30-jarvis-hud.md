# Jarvis HUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional, always-on-top desktop HUD panel that visualizes the Jarvis voice core in real time (orb, waveform, streaming captions, status) and accepts voice **or** typed input, with a time-adaptive theme.

**Architecture:** The Python core publishes events to a no-op-safe in-process bus; a WebSocket server (started only with `--hud`) broadcasts them to a pywebview-hosted vanilla-web panel and dispatches commands back. The core is unchanged when the HUD is off.

**Tech Stack:** Python (`websockets`, `pywebview`), existing core (Ollama, Vosk, openWakeWord, fastembed, psutil), vanilla HTML/CSS/JS + `<canvas>`. All free/local; no Node, no paid services.

**Spec:** `docs/superpowers/specs/2026-05-30-jarvis-hud-design.md`

**Conventions:** Tests run with `python -m pytest` (config in `pyproject.toml`, `pythonpath=["."]`). Commit messages end with the repo's `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer. Work on branch `feature/jarvis-hud`.

---

## File Structure

**New files:**
- `core/hud/__init__.py` — package marker.
- `core/hud/events.py` — no-op-safe `emit()` + thread-safe event bus + `drain()`.
- `core/hud/theming.py` — pure `theme_for_hour()`.
- `core/hud/ws_server.py` — async WebSocket server: broadcast bus events, dispatch commands.
- `core/hud/stats.py` — `build_stats_payload()` + periodic stats/theme emitter thread.
- `hud/__init__.py`, `hud/__main__.py` — `python -m hud` entry.
- `hud/window.py` — pywebview window config.
- `hud/web/index.html`, `style.css`, `app.js`, `orb.js`, `waveform.js`, `theme.js` — the panel UI.
- Tests: `tests/test_embedder.py`, `tests/test_hud_theming.py`, `tests/test_hud_events.py`, `tests/test_process_query.py`, `tests/test_hud_ws_dispatch.py`, `tests/test_hud_stats.py`.

**Modified files:**
- `core/memory/embedder.py` — lazy model init.
- `config/settings.py` — HUD config constants.
- `app.py` — extract `process_query()`, add `--hud` flag, emit points, spawn HUD.
- `core/ai/ollama_engine.py` — emit `assistant_token`/`assistant_done`.
- `core/speech/openwakeword_listener.py` — emit `level`.
- `core/speech/tts_queue.py` — emit `state="speaking"`.
- `requirements.txt` (or `requirements-hud.txt`) — add `websockets`, `pywebview`.
- `README.md`, `docs/ARCHITECTURE.md`, `CHANGELOG.md` — docs.

---

## Phase 0 — Enabling refactor

### Task 1: Lazy-initialize the embedder

Make `core/memory/embedder.py` import cheaply (no model download at import) so `core`/`app` are importable in CI tests.

**Files:**
- Modify: `core/memory/embedder.py`
- Test: `tests/test_embedder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_embedder.py
import core.memory.embedder as emb


class _FakeEmbedder:
    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_encode_wraps_string_and_uses_embedder(monkeypatch):
    fake = _FakeEmbedder()
    monkeypatch.setattr(emb, "_text_embedder", fake)
    out = emb.encode("hello")
    assert fake.calls == [["hello"]]
    assert len(out) == 1


def test_encode_passes_list_through(monkeypatch):
    fake = _FakeEmbedder()
    monkeypatch.setattr(emb, "_text_embedder", fake)
    out = emb.encode(["a", "b"])
    assert fake.calls == [["a", "b"]]
    assert len(out) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_embedder.py -v`
Expected: FAIL — `_text_embedder` is created at import (current code) so the monkeypatch target differs / model load occurs.

- [ ] **Step 3: Make the embedder lazy**

Replace the bottom of `core/memory/embedder.py` (the eager `_text_embedder = TextEmbedding(...)` and `encode`) with:

```python
# core/memory/embedder.py  (replace the fastembed import + instantiation + encode)
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

CACHE_DIR = "models/embeddings"


_text_embedder = None


def _get_embedder():
    global _text_embedder

    if _text_embedder is None:

        # Imported lazily so merely importing this module is cheap and does
        # not trigger a model download (keeps the core importable in CI).
        # pyrefly: ignore [missing-import]
        from fastembed import TextEmbedding

        _text_embedder = TextEmbedding(
            model_name=MODEL_NAME,
            cache_dir=CACHE_DIR,
        )

    return _text_embedder


def encode(texts):

    if isinstance(texts, str):

        texts = [texts]

    return list(
        _get_embedder().embed(texts)
    )
```

Keep the existing top-of-file env/logging setup (the `os.environ.setdefault(...)` and `logging.getLogger(...).setLevel(...)` lines). Remove the old module-level `from fastembed import TextEmbedding` line and the old `_text_embedder = TextEmbedding(...)` block.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_embedder.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Run full suite + lint**

Run: `python -m pytest` then `python -m flake8 . --select=E9,F63,F7,F82,F401 --exclude=venv,__pycache__ --count`
Expected: all tests pass; lint count `0`.

- [ ] **Step 6: Commit**

```bash
git add core/memory/embedder.py tests/test_embedder.py
git commit -m "refactor(memory): lazy-init embedder so core is import-cheap

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 1 — Config & pure helpers

### Task 2: HUD config + `theme_for_hour()`

**Files:**
- Modify: `config/settings.py`
- Create: `core/hud/__init__.py`, `core/hud/theming.py`
- Test: `tests/test_hud_theming.py`

- [ ] **Step 1: Add config constants**

Append to `config/settings.py`:

```python

# -------------------- #
# HUD (desktop overlay)
# -------------------- #

HUD_WS_HOST = "127.0.0.1"

HUD_WS_PORT = 8765

HUD_STATS_INTERVAL = 3.0

# Theme schedule (24h). Day -> cyan, evening -> gold, night -> frost.
HUD_THEME_DAY_START = 5

HUD_THEME_EVENING_START = 17

HUD_THEME_NIGHT_START = 21
```

- [ ] **Step 2: Create the package marker**

Create `core/hud/__init__.py` (empty file).

- [ ] **Step 3: Write the failing test**

```python
# tests/test_hud_theming.py
from core.hud.theming import theme_for_hour


def test_late_night_is_frost():
    assert theme_for_hour(4) == "frost"


def test_day_start_is_cyan():
    assert theme_for_hour(5) == "cyan"
    assert theme_for_hour(16) == "cyan"


def test_evening_is_gold():
    assert theme_for_hour(17) == "gold"
    assert theme_for_hour(20) == "gold"


def test_night_is_frost():
    assert theme_for_hour(21) == "frost"
    assert theme_for_hour(23) == "frost"
    assert theme_for_hour(0) == "frost"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `python -m pytest tests/test_hud_theming.py -v`
Expected: FAIL — `core.hud.theming` does not exist.

- [ ] **Step 5: Implement `theming.py`**

```python
# core/hud/theming.py
from config.settings import (
    HUD_THEME_DAY_START,
    HUD_THEME_EVENING_START,
    HUD_THEME_NIGHT_START,
)


def theme_for_hour(hour):
    """Map a 24h hour (0-23) to a HUD theme name: cyan / gold / frost."""

    if HUD_THEME_DAY_START <= hour < HUD_THEME_EVENING_START:

        return "cyan"

    if HUD_THEME_EVENING_START <= hour < HUD_THEME_NIGHT_START:

        return "gold"

    return "frost"
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_hud_theming.py -v`
Expected: PASS (4 passed).

- [ ] **Step 7: Commit**

```bash
git add config/settings.py core/hud/__init__.py core/hud/theming.py tests/test_hud_theming.py
git commit -m "feat(hud): add HUD config + theme_for_hour schedule

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Event bus (`core/hud/events.py`)

**Files:**
- Create: `core/hud/events.py`
- Test: `tests/test_hud_events.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hud_events.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hud_events.py -v`
Expected: FAIL — `core.hud.events` does not exist.

- [ ] **Step 3: Implement `events.py`**

```python
# core/hud/events.py
import queue
import time


_enabled = False

_bus = queue.Queue(maxsize=1000)


def enable():
    global _enabled
    _enabled = True


def disable():
    global _enabled
    _enabled = False


def is_enabled():
    return _enabled


def emit(event_type, **payload):
    """Publish an event to the HUD bus. No-op (and zero cost) when disabled."""

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_hud_events.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add core/hud/events.py tests/test_hud_events.py
git commit -m "feat(hud): add no-op-safe event bus

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 2 — Query pipeline refactor

### Task 4: Extract `process_query()` in `app.py`

Extract the per-query routing block from `main()` so both the voice loop and the future `text_query` command share it. Reduces `main()` complexity.

**Files:**
- Modify: `app.py`
- Test: `tests/test_process_query.py`

- [ ] **Step 1: Add `process_query()` to `app.py`**

Add this function above `main()` (after `_run_intent_handler`):

```python
def process_query(query, task_manager, source="voice"):
    """Route one recognized/typed query through the pipeline.

    `source` is "voice" or "text". Session/exit-word handling stays in the
    voice loop; this function only does profile capture, reminders, intent
    routing, the tool agent, and the LLM fallback.
    """

    from core.hud import events

    personal_info = extract_personal_info(query)

    if personal_info:

        update_profile(
            personal_info["key"],
            personal_info["value"]
        )

        logger.info(f"Profile Updated: {personal_info}")

    reminder = parse_reminder(query)

    if reminder:

        task_manager.add_reminder_in_minutes(
            reminder["minutes"],
            reminder["message"]
        )

        logger.info(f"Reminder Created: {reminder}")

        speak(
            f"Reminder set for "
            f"{reminder['minutes']} minutes."
        )

        return

    handler = route_intent(query)

    if handler:

        try:

            logger.info(f"Intent Handler: {handler.__name__}")

            _run_intent_handler(handler, query)

        except Exception as e:

            logger.exception(f"Intent Error: {e}")

            speak(
                "Something went wrong "
                "while executing that command."
            )

        return

    events.emit("state", state="thinking")

    tool = decide_tool(query)

    if tool != "none":

        logger.info(f"Executed Tool: {tool}")

        response = execute_tool(tool)

        if response:

            speak(response)

        return

    logger.info("Generating LLM response")

    response = ask_llm(query)

    logger.info("LLM response generated")

    save_memory(query, response)

    logger.info("Conversation saved to memory")
```

- [ ] **Step 2: Replace the inline block in `main()`**

In `main()`, replace everything from the `personal_info = extract_personal_info(query)` line through the final `logger.info("Conversation saved to memory")` line (the block after the EXIT_WORDS handling) with a single call:

```python
            process_query(query, task_manager)
```

Leave the EXIT_WORDS handling, `session.update_interaction()`, logging of the query, and the wake/`command()` logic intact.

- [ ] **Step 3: Write the test**

```python
# tests/test_process_query.py
import app


class _FakeTaskManager:
    def __init__(self):
        self.reminders = []

    def add_reminder_in_minutes(self, minutes, message):
        self.reminders.append((minutes, message))


def test_sets_reminder(monkeypatch):
    spoken = []
    monkeypatch.setattr(app, "speak", lambda t: spoken.append(t))
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    tm = _FakeTaskManager()
    app.process_query("remind me in 5 minutes to drink water", tm)
    assert tm.reminders == [(5, "drink water")]
    assert any("Reminder set" in s for s in spoken)


def test_routes_to_intent_handler(monkeypatch):
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    monkeypatch.setattr(app, "parse_reminder", lambda q: None)
    called = {}

    def fake_handler(query, speak):
        called["q"] = query

    fake_handler.__name__ = "handle_media_control"
    monkeypatch.setattr(app, "route_intent", lambda q: fake_handler)
    monkeypatch.setattr(app, "speak", lambda t: None)
    app.process_query("volume up", _FakeTaskManager())
    assert called["q"] == "volume up"


def test_llm_fallback_saves_memory(monkeypatch):
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    monkeypatch.setattr(app, "parse_reminder", lambda q: None)
    monkeypatch.setattr(app, "route_intent", lambda q: None)
    monkeypatch.setattr(app, "decide_tool", lambda q: "none")
    monkeypatch.setattr(app, "ask_llm", lambda q: "an answer")
    saved = {}
    monkeypatch.setattr(app, "save_memory", lambda q, r: saved.setdefault("v", (q, r)))
    monkeypatch.setattr(app, "speak", lambda t: None)
    app.process_query("what is python", _FakeTaskManager())
    assert saved["v"] == ("what is python", "an answer")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_process_query.py -v`
Expected: PASS (3 passed). (Requires Task 1's lazy embedder so `import app` is cheap.)

- [ ] **Step 5: Verify complexity dropped + suite green**

Run: `python -m pytest` then `python -m flake8 app.py --max-complexity=10 --max-line-length=127`
Expected: tests pass; no `C901` on `main`.

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_process_query.py
git commit -m "refactor(app): extract process_query() for voice + text reuse

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 3 — WebSocket server & stats

### Task 5: Command dispatch + async server (`core/hud/ws_server.py`)

**Files:**
- Create: `core/hud/ws_server.py`
- Test: `tests/test_hud_ws_dispatch.py`

- [ ] **Step 1: Write the failing test (pure dispatch)**

```python
# tests/test_hud_ws_dispatch.py
import core.hud.ws_server as ws


def setup_function():
    ws._handlers.clear()


def test_text_query_calls_handler_with_text():
    got = {}
    ws.register_handlers(text_query=lambda text: got.setdefault("t", text))
    ws._dispatch_command('{"type": "text_query", "text": "hello"}')
    assert got["t"] == "hello"


def test_wake_calls_zero_arg_handler():
    calls = []
    ws.register_handlers(wake=lambda: calls.append("wake"))
    ws._dispatch_command('{"type": "wake"}')
    assert calls == ["wake"]


def test_unknown_type_is_ignored():
    ws.register_handlers(stop=lambda: (_ for _ in ()).throw(AssertionError("should not run")))
    assert ws._dispatch_command('{"type": "foo"}') is None


def test_bad_json_is_ignored():
    assert ws._dispatch_command("not json") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hud_ws_dispatch.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement `ws_server.py`**

```python
# core/hud/ws_server.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_hud_ws_dispatch.py -v`
Expected: PASS (4 passed). (`import websockets` must be installed — see Task 11 deps; if running tests before installing, `pip install websockets` first.)

- [ ] **Step 5: Commit**

```bash
git add core/hud/ws_server.py tests/test_hud_ws_dispatch.py
git commit -m "feat(hud): WebSocket server with command dispatch + broadcast

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Stats + theme emitter (`core/hud/stats.py`)

**Files:**
- Create: `core/hud/stats.py`
- Test: `tests/test_hud_stats.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hud_stats.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hud_stats.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement `stats.py`**

```python
# core/hud/stats.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_hud_stats.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add core/hud/stats.py tests/test_hud_stats.py
git commit -m "feat(hud): periodic stats + theme emitter

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 4 — Wire the core to the HUD

### Task 7: `--hud` flag, handlers, emit points, spawn HUD

**Files:**
- Modify: `app.py`
- Modify: `core/ai/ollama_engine.py`
- Modify: `core/speech/openwakeword_listener.py`
- Modify: `core/speech/tts_queue.py`

- [ ] **Step 1: Add imports + argument parsing to `app.py`**

At the top of `app.py` add:

```python
import argparse
import os
import subprocess
```

Add a helper above `main()`:

```python
def _start_hud(session):
    """Enable the HUD event bus, wire commands, start servers, spawn the UI."""

    from core.hud import events, ws_server, stats

    events.enable()

    def _on_text_query(text):
        text = (text or "").lower().strip()
        if text:
            session.activate()
            process_query(text, _start_hud.task_manager, source="text")

    def _on_wake():
        session.activate()
        speak("Yes Boss?")

    def _on_stop():
        stop_speaking()
        from core.speech.tts_queue import clear_queue
        clear_queue()

    ws_server.register_handlers(
        text_query=_on_text_query,
        wake=_on_wake,
        stop=_on_stop,
    )

    ws_server.start_in_thread()
    stats.start()

    # Spawn the pywebview HUD as a separate process.
    subprocess.Popen(
        [os.sys.executable, "-m", "hud"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
```

- [ ] **Step 2: Parse `--hud` and start it in `main()`**

At the start of `main()` (after `logger.info("Starting Jarvis...")`), add:

```python
    parser = argparse.ArgumentParser(description="Jarvis voice assistant")
    parser.add_argument("--hud", action="store_true", help="Launch the desktop HUD")
    args = parser.parse_args()
```

After `task_manager.start()`, store a reference and conditionally start the HUD:

```python
    _start_hud.task_manager = task_manager

    if args.hud:
        _start_hud(session)
```

(`session` and `task_manager` are already created above those lines; ensure `_start_hud(session)` is called after both exist.)

- [ ] **Step 3: Add emit points in the `main()` voice loop**

Add `from core.hud import events` to the imports. In the loop:
- Right after `session.activate()` on wake: `events.emit("wake")`.
- Immediately before `query = command()`: `events.emit("state", state="listening")`.
- After `print(f"\nUser: {query}")`: `events.emit("transcript", role="user", text=query)`.
- When the session deactivates (both exit-word and timeout branches), add: `events.emit("state", state="idle")`.

- [ ] **Step 4: Emit assistant tokens in `core/ai/ollama_engine.py`**

Add `from core.hud import events` to imports. Inside the streaming loop, right after `full_response += token`, add:

```python
                    events.emit("assistant_token", text=token)
```

After the leftover-buffer flush, before `return full_response.strip()`, add:

```python
        events.emit("assistant_done", full_text=full_response.strip())
```

- [ ] **Step 5: Emit mic level in `core/speech/openwakeword_listener.py`**

Add `from core.hud import events` to imports. Inside `detect_wake_word`'s main `while True` loop, right after computing `audio_np`, add:

```python
            rms = float(np.sqrt(np.mean(audio_np.astype(np.float64) ** 2)))
            events.emit("level", rms=min(1.0, rms / 3000.0))
```

- [ ] **Step 6: Emit speaking state in `core/speech/tts_queue.py`**

Add `from core.hud import events` to imports. In `tts_worker`, wrap the speak call:

```python
        try:
            if text:
                events.emit("state", state="speaking")
                speak_sync(text)
        finally:
            tts_queue.task_done()
            if tts_queue.empty():
                events.emit("state", state="listening")
```

- [ ] **Step 7: Verify the core still imports and tests pass**

Run: `python -m pytest` then `python -c "import app"`
Expected: tests pass; `import app` succeeds with no error.

- [ ] **Step 8: Manual smoke test of events (throwaway client)**

Create a scratch file `scratch_ws.py`:

```python
import asyncio, json, websockets
async def main():
    async with websockets.connect("ws://127.0.0.1:8765") as ws:
        async for msg in ws:
            print(json.loads(msg))
asyncio.run(main())
```

Run `python app.py --hud` in one terminal (the pywebview window will error until Task 8/9 — that's fine; ignore it for now or temporarily comment out the `subprocess.Popen` line). In another terminal run `python scratch_ws.py`. Speak to Jarvis.
Expected: live JSON `state`, `wake`, `transcript`, `assistant_token`, `stats`, `theme`, `level` events stream in. Delete `scratch_ws.py` after.

- [ ] **Step 9: Commit**

```bash
git add app.py core/ai/ollama_engine.py core/speech/openwakeword_listener.py core/speech/tts_queue.py
git commit -m "feat(hud): --hud flag, command handlers, emit points

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 5 — pywebview host + web panel

### Task 8: HUD process shell (`hud/`)

**Files:**
- Create: `hud/__init__.py`, `hud/__main__.py`, `hud/window.py`

- [ ] **Step 1: Create the package marker**

Create `hud/__init__.py` (empty).

- [ ] **Step 2: Implement `hud/window.py`**

```python
# hud/window.py
import os

# pyrefly: ignore [missing-import]
import webview

from config.settings import (
    HUD_WS_HOST,
    HUD_WS_PORT,
)


def _web_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "web", "index.html")


def launch():
    ws_url = f"ws://{HUD_WS_HOST}:{HUD_WS_PORT}"

    url = f"file:///{_web_path().replace(os.sep, '/')}?ws={ws_url}"

    webview.create_window(
        "Jarvis",
        url=url,
        width=380,
        height=240,
        x=40,
        y=40,
        frameless=True,
        easy_drag=True,
        on_top=True,
        resizable=False,
        background_color="#05080f",
    )

    webview.start()
```

- [ ] **Step 3: Implement `hud/__main__.py`**

```python
# hud/__main__.py
from hud.window import launch


if __name__ == "__main__":
    launch()
```

- [ ] **Step 4: Manual verify the window opens**

Run: `python -m hud`
Expected: a small frameless window opens at the top-left (blank until Task 9 adds the page content). It will show a missing-file or empty page; that's fine. Close it.

- [ ] **Step 5: Commit**

```bash
git add hud/__init__.py hud/__main__.py hud/window.py
git commit -m "feat(hud): pywebview window shell (python -m hud)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Panel markup + theme styles

**Files:**
- Create: `hud/web/index.html`, `hud/web/style.css`

- [ ] **Step 1: Create `hud/web/index.html`**

```html
<!DOCTYPE html>
<html lang="en" data-theme="cyan">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="style.css" />
  <title>Jarvis</title>
</head>
<body>
  <div id="panel">
    <div class="top">
      <canvas id="orb" width="44" height="44"></canvas>
      <canvas id="wave" width="150" height="26"></canvas>
      <span id="pill" class="pill">idle</span>
    </div>
    <div class="caps">
      <div id="cap-user" class="cap u"></div>
      <div id="cap-jarvis" class="cap j"></div>
    </div>
    <div class="status">
      <span id="st-model" class="pill">—</span>
      <span id="st-cpu" class="pill">CPU —</span>
      <span id="st-batt" class="pill">— </span>
      <span id="st-net" class="pill">offline</span>
    </div>
    <form id="form">
      <input id="input" type="text" placeholder="Type to Jarvis…" autocomplete="off" />
    </form>
  </div>
  <script src="theme.js"></script>
  <script src="orb.js"></script>
  <script src="waveform.js"></script>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `hud/web/style.css`**

```css
:root {
  --bg1: #0a2238; --bg2: #06121f; --border: rgba(70,200,255,.28);
  --glow: rgba(40,160,255,.20); --accent: #9af0ff; --accent2: #1aa0e6;
  --user: #8fb3d6; --jar: #9af0ff; --pill: #bfe9ff; --pillbg: rgba(10,30,52,.7);
  --font: ui-monospace, Menlo, Consolas, monospace;
}
:root[data-theme="gold"] {
  --bg1: #0c0f0e; --bg2: #0a0805; --border: rgba(255,196,87,.38);
  --glow: rgba(255,180,60,.16); --accent: #ffe6a8; --accent2: #ff9d2f;
  --user: #7fb6a8; --jar: #ffd98a; --pill: #ffd98a; --pillbg: rgba(28,20,6,.7);
}
:root[data-theme="frost"] {
  --bg1: rgba(26,36,51,.75); --bg2: rgba(13,16,24,.75); --border: rgba(255,255,255,.14);
  --glow: rgba(106,168,255,.18); --accent: #eaf3ff; --accent2: #6aa8ff;
  --user: #9fb0c8; --jar: #eaf1ff; --pill: #cfe0ff; --pillbg: rgba(255,255,255,.06);
  --font: system-ui, -apple-system, "Segoe UI", sans-serif;
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; background: transparent; overflow: hidden;
  font-family: var(--font); -webkit-user-select: none; user-select: none; }
#panel {
  height: 100%; padding: 12px; display: flex; flex-direction: column; gap: 9px;
  border-radius: 16px; border: 1px solid var(--border);
  background: radial-gradient(120% 120% at 20% 0%, var(--bg1), var(--bg2));
  box-shadow: 0 0 26px var(--glow) inset, 0 8px 30px rgba(0,0,0,.4);
  backdrop-filter: blur(14px);
  transition: background .6s ease, border-color .6s ease, box-shadow .6s ease;
}
.top { display: flex; align-items: center; gap: 9px; }
#wave { flex: 1; height: 26px; }
.pill { font-size: 10px; letter-spacing: .07em; text-transform: uppercase;
  color: var(--pill); border: 1px solid var(--border); background: var(--pillbg);
  border-radius: 20px; padding: 2px 8px; white-space: nowrap;
  transition: color .6s ease, border-color .6s ease; }
.caps { flex: 1; display: flex; flex-direction: column; gap: 4px; overflow: hidden; }
.cap { font-size: 11px; line-height: 1.5; }
.cap.u { color: var(--user); }
.cap.j { color: var(--jar); text-shadow: 0 0 8px var(--glow); min-height: 16px; }
.status { display: flex; gap: 6px; flex-wrap: wrap; }
#form { margin: 0; }
#input { width: 100%; font-family: var(--font); font-size: 11px; color: var(--accent);
  background: var(--pillbg); border: 1px solid var(--border); border-radius: 10px;
  padding: 7px 10px; outline: none; }
#input::placeholder { color: var(--user); opacity: .7; }
```

- [ ] **Step 3: Commit**

```bash
git add hud/web/index.html hud/web/style.css
git commit -m "feat(hud): panel markup + 3 theme stylesheets

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Theme + WebSocket client logic

**Files:**
- Create: `hud/web/theme.js`, `hud/web/app.js`

- [ ] **Step 1: Create `hud/web/theme.js`**

```javascript
// theme.js — applies server theme events; manual override persists locally.
const Theme = (() => {
  const KEY = "jarvis-theme-override"; // "auto" | "cyan" | "gold" | "frost"
  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
  }
  function override() {
    return localStorage.getItem(KEY) || "auto";
  }
  function setOverride(v) {
    localStorage.setItem(KEY, v);
  }
  function onServerTheme(theme) {
    if (override() === "auto") apply(theme);
  }
  // If a manual override is set, apply it immediately on load.
  const o = override();
  if (o !== "auto") apply(o);
  return { apply, override, setOverride, onServerTheme };
})();
```

- [ ] **Step 2: Create `hud/web/app.js`**

```javascript
// app.js — connect to the core, render events, send commands.
(() => {
  const params = new URLSearchParams(location.search);
  const WS_URL = params.get("ws") || "ws://127.0.0.1:8765";

  const pill = document.getElementById("pill");
  const capUser = document.getElementById("cap-user");
  const capJarvis = document.getElementById("cap-jarvis");
  const stModel = document.getElementById("st-model");
  const stCpu = document.getElementById("st-cpu");
  const stBatt = document.getElementById("st-batt");
  const stNet = document.getElementById("st-net");
  const form = document.getElementById("form");
  const input = document.getElementById("input");

  let ws = null;
  let backoff = 500;

  function setState(state) {
    pill.textContent = state;
    if (window.Orb) Orb.setState(state);
  }

  function handle(evt) {
    switch (evt.type) {
      case "ready":
        if (evt.state) setState(evt.state);
        if (evt.theme) Theme.onServerTheme(evt.theme);
        break;
      case "state": setState(evt.state); break;
      case "wake": if (window.Orb) Orb.flash(); break;
      case "transcript":
        capUser.textContent = "You: " + evt.text;
        capJarvis.textContent = "";
        break;
      case "assistant_token":
        capJarvis.textContent += evt.text;
        break;
      case "assistant_done":
        if (evt.full_text) capJarvis.textContent = "Jarvis: " + evt.full_text;
        break;
      case "theme": Theme.onServerTheme(evt.theme); break;
      case "level": if (window.Waveform) Waveform.push(evt.rms); break;
      case "stats":
        stModel.textContent = evt.model || "—";
        stCpu.textContent = "CPU " + Math.round(evt.cpu) + "%";
        stBatt.textContent = evt.battery_pct == null
          ? "—" : Math.round(evt.battery_pct) + "%" + (evt.charging ? " ⚡" : "");
        stNet.textContent = evt.online ? "online" : "offline";
        break;
      case "reminder_fired":
        capJarvis.textContent = "Reminder: " + evt.message;
        break;
      case "error":
        capJarvis.textContent = "⚠ " + evt.message;
        break;
    }
  }

  function send(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
  }

  function connect() {
    ws = new WebSocket(WS_URL);
    ws.onopen = () => { backoff = 500; };
    ws.onmessage = (m) => { try { handle(JSON.parse(m.data)); } catch (e) {} };
    ws.onclose = () => {
      setState("idle");
      setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, 5000);
    };
    ws.onerror = () => { try { ws.close(); } catch (e) {} };
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    capUser.textContent = "You: " + text;
    capJarvis.textContent = "";
    send({ type: "text_query", text });
    input.value = "";
  });

  connect();
})();
```

- [ ] **Step 3: Manual verify end-to-end (captions + status)**

Terminal 1: `python app.py --hud` (with `subprocess.Popen` re-enabled). The panel should open and connect.
Expected: status row populates within ~3s (model/CPU/battery/online); say "hey jarvis" → pill shows `listening`; speak → `You:` line appears; Jarvis reply streams into the `Jarvis:` line; theme matches time of day. Type a message + Enter → it routes through and Jarvis responds.

- [ ] **Step 4: Commit**

```bash
git add hud/web/theme.js hud/web/app.js
git commit -m "feat(hud): WebSocket client, captions, status, text input, reconnect

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Orb + waveform canvas + dependencies

**Files:**
- Create: `hud/web/orb.js`, `hud/web/waveform.js`
- Modify: `requirements.txt`, `requirements-dev.txt`

- [ ] **Step 1: Create `hud/web/orb.js`**

```javascript
// orb.js — animated state orb on a <canvas>.
const Orb = (() => {
  const canvas = document.getElementById("orb");
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height, cx = W / 2, cy = H / 2;
  let state = "idle";
  let flashUntil = 0;
  let t = 0;

  function accent() {
    return getComputedStyle(document.documentElement)
      .getPropertyValue("--accent2").trim() || "#1aa0e6";
  }
  function accentLight() {
    return getComputedStyle(document.documentElement)
      .getPropertyValue("--accent").trim() || "#9af0ff";
  }

  function setState(s) { state = s; }
  function flash() { flashUntil = performance.now() + 250; }

  function draw() {
    t += 0.05;
    ctx.clearRect(0, 0, W, H);
    let base = 13;
    if (state === "listening") base = 13 + Math.sin(t * 3) * 2;
    else if (state === "thinking") base = 13 + Math.sin(t * 6) * 1.2;
    else if (state === "speaking") base = 14 + Math.sin(t * 9) * 3;
    else base = 12 + Math.sin(t * 1.5) * 1; // idle breathing
    if (performance.now() < flashUntil) base += 4;

    const grad = ctx.createRadialGradient(cx - 4, cy - 4, 2, cx, cy, base + 6);
    grad.addColorStop(0, accentLight());
    grad.addColorStop(0.5, accent());
    grad.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, base + 6, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = accent();
    ctx.beginPath();
    ctx.arc(cx, cy, base, 0, Math.PI * 2);
    ctx.fill();

    if (state === "thinking") {
      ctx.strokeStyle = accentLight();
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, base + 5, t % (Math.PI * 2), (t % (Math.PI * 2)) + 1.5);
      ctx.stroke();
    }
    requestAnimationFrame(draw);
  }
  draw();
  return { setState, flash };
})();
```

- [ ] **Step 2: Create `hud/web/waveform.js`**

```javascript
// waveform.js — bar waveform fed by `level` events, decays when idle.
const Waveform = (() => {
  const canvas = document.getElementById("wave");
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const N = 24;
  const bars = new Array(N).fill(0);

  function accent() {
    return getComputedStyle(document.documentElement)
      .getPropertyValue("--accent2").trim() || "#1aa0e6";
  }

  function push(rms) {
    bars.push(Math.max(0, Math.min(1, rms)));
    if (bars.length > N) bars.shift();
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    const bw = W / N;
    ctx.fillStyle = accent();
    for (let i = 0; i < bars.length; i++) {
      bars[i] *= 0.92; // decay
      const h = Math.max(2, bars[i] * H);
      ctx.fillRect(i * bw + 1, (H - h) / 2, bw - 2, h);
    }
    requestAnimationFrame(draw);
  }
  draw();
  return { push };
})();
```

- [ ] **Step 3: Add dependencies**

Append to `requirements.txt`:

```text

# Desktop HUD (only used with `python app.py --hud`)
websockets>=12.0
pywebview>=5.0
```

(These are also pulled into `requirements-dev.txt` via its `-r requirements.txt`, so CI installs them and the `import websockets` tests run.)

- [ ] **Step 4: Manual verify orb + waveform**

Run: `python app.py --hud`
Expected: orb breathes when idle, ripples while listening, spins an arc while thinking, pulses while speaking, and flashes on wake; the waveform reacts to your voice during wake-word listening; themes cross-fade if you cross a time boundary (or test by temporarily forcing `theme_for_hour`).

- [ ] **Step 5: Full suite + lint**

Run: `python -m pytest` then `python -m flake8 . --select=E9,F63,F7,F82,F401 --exclude=venv,__pycache__ --count`
Expected: all tests pass; lint `0`.

- [ ] **Step 6: Commit**

```bash
git add hud/web/orb.js hud/web/waveform.js requirements.txt
git commit -m "feat(hud): canvas orb + waveform; add websockets/pywebview deps

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 6 — Docs & release

### Task 12: README, architecture, changelog

**Files:**
- Modify: `README.md`, `docs/ARCHITECTURE.md`, `CHANGELOG.md`

- [ ] **Step 1: README — add a Desktop HUD section**

Under Core Features (and/or near Run), add:

```markdown
### Desktop HUD (optional)

Launch the always-on-top HUD panel — animated orb, live waveform, streaming
captions, type-to-Jarvis input, and a status row — with a time-adaptive theme
(cyan by day, gold in the evening, frosted at night):

```bash
python app.py --hud
```

The HUD is a separate pywebview window that connects to the core over a local
WebSocket. The voice assistant runs exactly as normal without `--hud`.
```

Also add a hero GIF placeholder near the top: `![Jarvis HUD](docs/media/hud-demo.gif)` and record the GIF during verification.

- [ ] **Step 2: ARCHITECTURE.md — add the HUD layer**

Add a row to the module map table: `| core/hud/ + hud/ | Optional desktop HUD: event bus, WebSocket server, stats/theme emitter (Python) and a pywebview-hosted vanilla-web panel |` and a short "Desktop HUD" subsection summarizing the WS event/command contract (reference the spec).

- [ ] **Step 3: CHANGELOG + version bump**

Prepend a `## v3.2.0` entry summarizing the HUD feature, and bump the version string in `pyproject.toml` to `3.2.0`.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/ARCHITECTURE.md CHANGELOG.md pyproject.toml
git commit -m "docs: document the desktop HUD; bump to v3.2.0

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 5: Open a PR**

```bash
git push -u origin feature/jarvis-hud
gh pr create --fill --base main
```

---

## Self-Review

**Spec coverage:**
- §1 features — orb (Task 11), waveform (Task 11), captions (Task 10), text input (Task 10), status row (Task 10/6), time theme (Tasks 2/6/10). ✓
- §3 tech decisions — pywebview (Task 8), vanilla web (Tasks 9-11), WebSocket (Task 5), two-process spawn (Task 7), Python theme logic (Tasks 2/6). ✓
- §5 contract — events emitted across Tasks 6-7; commands dispatched Task 5; wired Task 7. ✓ (`reminder_fired`/`error` are rendered in `app.js` (Task 10); emitting `reminder_fired` from `task_manager._fire` is a one-line fast-follow noted in the spec's non-v1 toast — optional, not blocking.)
- §6 Python changes — events (Task 3), ws_server (Task 5), stats (Task 6), process_query (Task 4), config (Task 2), emit points (Task 7). ✓
- §7 frontend — all files in Tasks 9-11. ✓
- §8 resilience — `emit` no-op + lossy bus (Task 3), auto-reconnect (Task 10), HUD optional (Task 7 only on `--hud`). ✓
- §9 tests — embedder, theming, events, process_query, ws dispatch, stats all covered. ✓
- §10 build order — Tasks map 1:1 to the 5 build steps. ✓

**Placeholder scan:** No "TBD"/"add error handling"-style gaps; all code steps contain full code. The README hero GIF is produced during verification (an asset, not code).

**Type/name consistency:** `emit`/`drain`/`enable`/`is_enabled` (events) used consistently; `register_handlers`/`_dispatch_command`/`start_in_thread` (ws_server) consistent; `build_stats_payload`/`start`/`stop` (stats) consistent; `process_query(query, task_manager, source)` signature matches its callers in Tasks 4 and 7; `Orb.setState/flash`, `Waveform.push`, `Theme.onServerTheme` match `app.js` call sites.

One refinement applied during review: the `reminder_fired` event is rendered client-side but only *emitted* as an optional fast-follow (one line in `TaskManager._fire`) — flagged here rather than forcing it into v1, consistent with the spec's non-goals.
