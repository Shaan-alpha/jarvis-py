# Jarvis HUD — Design Spec

- **Date:** 2026-05-30
- **Status:** Draft for review
- **Owner:** Shaan Satsangi
- **Feature:** A desktop "HUD panel" overlay for jarvis-py — the headline, screenshot-worthy feature to drive GitHub adoption.

---

## 1. Summary

Add a **desktop HUD** to jarvis-py: a compact, always-on-top, corner-docked
"control-center" panel that visualizes the assistant in real time and lets the
user interact by voice **or** text.

The HUD shows:

- An animated **orb** reflecting voice state (idle / listening / thinking / speaking).
- A live **waveform** driven by microphone level.
- **Streaming captions** — the user's recognized speech and Jarvis's reply as it streams.
- A **type-to-Jarvis** text input (use it with no mic).
- A **status row**: CPU %, battery %/charging, active model, online/offline.

The HUD theme **auto-switches by time of day** — cyan (day), gold (evening),
frosted (night) — with a manual override.

The HUD is a **passive, optional observer**. The Python voice core runs exactly
as it does today when the HUD is off; nothing in `core/` depends on the HUD
unless `--hud` is passed.

### Non-goals (v1)

Reminders panel, conversation/memory viewer, settings UI, system tray, global
hotkey, push-to-talk, and a true mic-tap waveform *during* command capture are
all explicitly **fast-follow**, not v1.

---

## 2. Constraints

- **Zero cost / free + local only.** No paid APIs, no cloud services, no paid
  signing or hosting. Every dependency is free and open-source. (Google STT
  continues to use the existing free `speech_recognition` endpoint; no key.)
- **Windows-first** (matches the current project), but the web frontend and WS
  contract are portable.
- **Do not regress the working voice core.** The core must remain runnable and
  byte-for-byte behaviorally identical without `--hud`.
- Must extend the existing CI-safe, pure-Python test suite.

---

## 3. Technology decisions

| Concern | Decision | Why |
|---|---|---|
| Window shell | **pywebview** (Python, pip, free) | Frameless / always-on-top / drag panel using the Windows-bundled WebView2. Keeps the repo single-language; reuses the HTML/CSS mockups verbatim. |
| Frontend | **Vanilla HTML + CSS + JS** (`<canvas>` for orb/waveform) | No Node, no build step. The panel is small enough that a framework adds friction, not value. |
| Core ↔ HUD transport | **WebSocket** (`websockets` lib, free) on `127.0.0.1` | Keeps the proven voice loop on the main thread (least invasive); HUD is a decoupled, restartable client; same web app could later be wrapped in Tauri/Electron with no contract change. |
| Process model | **Two-process, HUD attaches** | `python app.py --hud` boots the WS server (core on main thread) and auto-spawns the HUD subprocess (`python -m hud`). One-click `.exe` bundling via PyInstaller is a documented fast-follow. |
| Theme schedule | Computed in **Python** (`theme_for_hour`), cutoffs in `settings.py`, emitted as a `theme` event | Configurable and unit-testable; client only applies CSS + manual override. |

**Rejected alternatives:** Tauri+React (adds Rust+Node toolchains — toolchain
friction and a higher contributor bar, for no visual gain at the panel form
factor); PyQt/PySide QML (heavy dep, can't reuse the web mockups); embedding
Python via PyO3 (fragile with audio/ML deps); plain browser tab (not an
always-on-top desktop overlay).

---

## 4. Architecture

```text
┌───────────────────────────────────────┐     ws://127.0.0.1:8765      ┌──────────────────────────────┐
│   PYTHON CORE  (app.py, main thread)   │  ───────── events ────────▶  │   HUD  (python -m hud)        │
│                                        │  ◀──────── commands ───────   │   pywebview window            │
│   voice loop · LLM · memory · tasks    │       (JSON over WS)          │   loads hud/web/index.html    │
│                                        │                               │                              │
│   core/hud/ (only active with --hud)   │                               │   app.js  ── WS client       │
│     events.emit()  ── in-proc bus      │                               │   orb.js / waveform.js       │
│     ws_server      ── broadcast+recv   │                               │   theme.js (clock + override)│
│     stats          ── cpu/batt/theme   │                               │                              │
└───────────────────────────────────────┘                               └──────────────────────────────┘
```

**Principle:** the core *publishes* what it's already doing. A new `core/hud/`
package exposes `emit(type, **payload)` that is a **no-op when the HUD is
disabled**. Core modules call it at the points where they already log; the WS
server (started only with `--hud`) broadcasts those events to connected HUD
clients and dispatches commands back into the core.

---

## 5. WebSocket contract

All messages are JSON objects with a `type` field and a `ts` (epoch seconds).

### 5.1 Events — Core → HUD

| `type` | Payload | Emitted when |
|---|---|---|
| `ready` | `{version, state, theme}` | On each client connect (HUD re-syncs) |
| `state` | `{state}`: `idle⏐listening⏐thinking⏐speaking` | Orb animation + status pill |
| `wake` | `{}` | Wake word detected (orb flash) |
| `transcript` | `{role:"user", text}` | After STT resolves the user's speech |
| `assistant_token` | `{text}` | Each streamed LLM token |
| `assistant_done` | `{full_text}` | End of a reply |
| `theme` | `{theme}`: `cyan⏐gold⏐frost` | On connect and when the clock crosses a cutoff |
| `stats` | `{cpu, battery_pct, charging, model, online}` | Every `HUD_STATS_INTERVAL` seconds (~3s) |
| `level` | `{rms}` (0.0–1.0) | While frames are available (wake/idle listening) |
| `reminder_fired` | `{message}` | A reminder triggers (toast only; no panel in v1) |
| `error` | `{message}` | Recoverable error → brief error state |

### 5.2 Commands — HUD → Core

| `type` | Payload | Effect |
|---|---|---|
| `text_query` | `{text}` | Inject typed text into the same pipeline as a spoken query (`process_query`) |
| `wake` | `{}` | "Activate" — same effect as saying "hey jarvis" |
| `stop` | `{}` | Barge-in: `stop_speaking()` + clear the TTS queue |

Theme override is **client-side only** (localStorage) and never sent to the core.

---

## 6. Python changes

### 6.1 New package `core/hud/`

- **`events.py`**
  - Module-level `_enabled = False` and a thread-safe `queue.Queue` bus.
  - `enable()` flips it on (called by `app.py` under `--hud`).
  - `emit(type, **payload)` → returns immediately if disabled; else timestamps
    and enqueues a dict. Cheap and import-safe; no dependency on the WS layer.
- **`ws_server.py`**
  - Async `websockets` server bound to `HUD_WS_HOST:HUD_WS_PORT`.
  - A broadcaster task drains the bus queue and sends to all clients.
  - A receiver per client parses commands and calls registered handlers.
  - `register_handlers(text_query=..., wake=..., stop=...)` is called by `app.py`.
  - `start_in_thread()` runs the asyncio loop in a daemon thread.
  - On connect: send `ready` + current `state` + current `theme`.
- **`stats.py`**
  - Daemon thread emitting `stats` every `HUD_STATS_INTERVAL` (reusing
    `psutil` like `core/automation/system.py`, plus `is_online()` and
    `MODEL_NAME`).
  - Also tracks the clock; emits a `theme` event when `theme_for_hour(now)`
    changes.
  - `theme_for_hour(hour) -> "cyan"|"gold"|"frost"` is a pure function driven by
    settings cutoffs (unit-tested).

### 6.2 `app.py` refactor

- Extract the per-iteration query handling (profile capture → reminder → fast
  router → tool agent → LLM fallback) from `main()` into
  **`process_query(query, source="voice")`**. Both the voice loop and the
  `text_query` command call it. Side benefit: removes the `C901` complexity
  warning the audit flagged on `main()`.
- Add `argparse` with `--hud`. When set: `events.enable()`,
  `ws_server.register_handlers(...)`, `ws_server.start_in_thread()`,
  start `stats`, then **spawn the HUD subprocess** (`python -m hud`, or the
  bundled executable). Without `--hud`: unchanged behavior, HUD code never imported.
- Add **emit points** (all no-op-safe):
  - `state="listening"` around `command()`; `wake` + handling after `detect_wake_word()`.
  - `transcript` (user) once a query is recognized.
  - `state="thinking"` before tool-agent / LLM; `state="speaking"` when TTS starts; `state="idle"` on sleep.
- `core/ai/ollama_engine.py`: emit `assistant_token` in the existing token loop
  and `assistant_done` at the end (next to the existing `print`/`add_to_queue`).
- `core/speech/openwakeword_listener.py`: emit `level` (normalized RMS) from the
  existing frame-read loop (cheap; frames already in hand).

### 6.3 Config additions (`config/settings.py`)

```python
HUD_WS_HOST = "127.0.0.1"
HUD_WS_PORT = 8765
HUD_STATS_INTERVAL = 3.0
HUD_THEME_DAY_START = 5      # 05:00 -> cyan
HUD_THEME_EVENING_START = 17 # 17:00 -> gold
HUD_THEME_NIGHT_START = 21   # 21:00 -> frost (until 04:59)
```

### 6.4 Dependencies

- Runtime (core, only used with `--hud`): **`websockets`** (pin a current free version).
- HUD process: **`pywebview`** (pin a current free version).
- Both added to `requirements.txt` (or an optional `requirements-hud.txt`);
  decision recorded at planning time. They are not imported unless the HUD runs.

---

## 7. Frontend (`hud/web/`, no build step)

- **`index.html`** — the panel markup: header row (orb + waveform + status pill),
  caption area (user + assistant lines), status row (model/cpu/battery/online),
  text input.
- **`style.css`** — layout + three themes as CSS custom properties switched via
  `:root[data-theme="cyan|gold|frost"]`; ~600ms cross-fade on `--*` transitions;
  frosted-glass panel background (works without window transparency).
- **`app.js`** — opens the WS, dispatches events to renderers, sends commands;
  **auto-reconnect with backoff**; renders captions (append `assistant_token`,
  finalize on `assistant_done`), status pill from `state`, status row from `stats`.
- **`orb.js`** — `<canvas>` orb: idle breathing, listening ripple, thinking spin,
  speaking pulse scaled by `level`.
- **`waveform.js`** — `<canvas>` bars from `level` (decay to flat when idle).
- **`theme.js`** — applies server `theme` events; manual override + "follow clock"
  toggle persisted in `localStorage` (override wins over server theme).

### `hud/` Python host

- **`window.py`** — `webview.create_window(..., frameless=True, on_top=True,
  easy_drag=True, width/height, x/y` corner-docked`)` loading `web/index.html`
  via file path. `webview.start()` on the main thread of the HUD process.
- **`__main__.py`** — entry for `python -m hud`.

---

## 8. Error handling & resilience

- **HUD optional:** core imports nothing from `hud/`/`core/hud/` unless `--hud`.
- **WS down / HUD closed:** core continues; emits are dropped if no client.
- **Client reconnect:** backoff loop; on reconnect the server replays `ready` +
  current `state`/`theme` so the panel re-syncs.
- **HUD subprocess crash:** logged; the voice core is unaffected. (Auto-restart
  is a fast-follow, not v1.)
- **Bus backpressure:** bounded queue; if it fills (HUD stalled), drop oldest
  `level`/`stats` events (lossy by design) but never block the voice loop.

---

## 9. Testing

Extends the pure-Python, CI-safe suite added in the audit pass (no audio/display
deps, no Node):

- `events.emit()` payload shape + timestamp; no-op when disabled.
- `ws_server` command dispatch routes `text_query`/`wake`/`stop` to registered
  handlers (handlers mocked; no real socket needed for the dispatch unit).
- `theme_for_hour()` boundaries: `04:59→frost`, `05:00→cyan`, `16:59→cyan`,
  `17:00→gold`, `20:59→gold`, `21:00→frost`.
- `stats` payload shape with `psutil` mocked.
- `process_query()` routes identically for `source="voice"` vs `source="text"`
  (router/tool-agent/LLM selection unchanged).

Frontend JS is verified manually (and via the throwaway WS client in build
step 2). Keeping JS logic thin keeps it out of the automated suite without a
Node toolchain.

---

## 10. Build sequence (each step independently verifiable)

1. `core/hud/events.py` + `process_query()` refactor + config + `theme_for_hour`
   (+ unit tests). Core still runs headless and green.
2. `core/hud/ws_server.py` + `stats.py` + `--hud` flag + emit points. Verify with
   a throwaway WS client (`wscat` or a 10-line script) — see live JSON events.
3. `hud/` pywebview window + static panel: connects, shows state/captions/stats,
   sends `text_query`/`wake`/`stop`.
4. `orb.js` + `waveform.js` canvas rendering + theme cross-fades.
5. README hero GIF + `--hud` quickstart docs. Fast-follow: PyInstaller one-click `.exe`.

---

## 11. Documentation & release

- README: a hero GIF of the HUD at the top, a "Desktop HUD" section, and the
  `python app.py --hud` quickstart.
- `docs/ARCHITECTURE.md`: add the HUD layer to the module map + lifecycle.
- CHANGELOG + version bump (project convention) at integration time.
- Set GitHub topics, enable Discussions, add a couple of `good first issue`s
  around the fast-follow items (reminders panel, settings UI, mic-tap waveform).

---

## 12. Open questions / decisions deferred to planning

- Pin exact free versions of `websockets` and `pywebview`; choose
  `requirements.txt` vs optional `requirements-hud.txt`.
- Exact panel dimensions + default screen corner.
- Whether the audit's flagged dead code (`schedule()`, `social_media()`,
  `warm_up()`) is removed in the same branch or separately.
