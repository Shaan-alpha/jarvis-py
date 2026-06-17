# Spec — Latency Instrumentation (v3.5, piece 1)

> Date: 2026-06-17 · Milestone: v3.5 Responsiveness & Efficiency · Status: design

## Why

v3.5 is the speed milestone. Every other piece (TTS engine reuse, warm-start,
faster routing, model bake-off) claims to make Jarvis faster — but today there is
no measurement, so "faster" is a vibe. This piece adds **per-stage turn timing**
so the rest of v3.5 is evidence-based and a latency budget can be enforced.

It is deliberately the *first* piece: it changes no behavior, only observes.

## Goal / non-goals

**Goal:** record the wall-clock time of each stage of a single turn, log a compact
summary per turn, and (when the HUD is on) emit it so the panel can show last-turn
latency. Cheap enough to leave always on.

**Non-goals:** no profiling/flamegraphs, no persistence/history of timings, no
percentile aggregation, no behavior changes. STT/wake-stage wiring is a follow-up
(this slice covers the routing + LLM + TTS stages, which are where v3.5's other
work will move the numbers).

## Design

### Core: a pure `Timeline` (unit-testable, no I/O)

`core/utils/metrics.py`:

- `Timeline(label, clock=time.perf_counter)` — created at turn start; records the
  start time. `clock` is injectable so tests are deterministic.
- `.mark(stage)` — record `stage -> elapsed_since_start`. Idempotent-safe: a
  repeated stage keeps the **first** occurrence (e.g. `first_token` fires once).
- `.deltas()` — ordered list of `(stage, ms_since_prev)` between consecutive marks.
- `.total_ms()` — elapsed start → last mark.
- `.summary()` — compact one-line string, e.g.
  `turn[text] route=12ms ttft=640ms first_audio=120ms total=1180ms`.

The `Timeline` is a plain value object: give it marks, ask it for deltas/summary.
No globals, no logging — trivial to test.

### Thin ambient API (so modules don't thread a Timeline through every call)

The pipeline spans `app.process_query`, `ollama_engine`, and `tts_queue` across
threads (voice loop vs HUD text thread). Passing a `Timeline` through every
signature is invasive, so the module also offers a **thread-local current
timeline**:

- `start_turn(label) -> Timeline` — create one and set it as current for this thread.
- `mark(stage)` — mark the current thread's timeline; **no-op if none active**
  (so `ollama_engine` marking `first_token` is safe even when called outside a turn,
  e.g. in tests).
- `end_turn()` — finalize: `logger.info(summary)`, emit a HUD `metrics` event, clear
  the thread-local. Returns the Timeline (for callers/tests).

Thread-local keeps the HUD text-query thread and the voice loop from clobbering each
other's timing (mirrors the cache-lock reasoning from the audit).

### Wiring (minimal, this slice)

- `app.process_query`: `start_turn(source)` at entry; `mark("routed")` once routing
  decides; `end_turn()` at every return path (reminder, tool, llm, empty).
- `ollama_engine`: `mark("first_token")` on the first streamed token;
  `mark("first_audio")` when the first sentence is queued to TTS.

Stages captured this slice: `start → routed → first_token → first_audio → done`.
Follow-up: `wake`, `listen`, `heard` (STT) — needs marks in the voice loop / HUD
entry, tracked as a separate task so this stays small.

### HUD

`end_turn()` emits `events.emit("metrics", summary=..., total_ms=..., stages={...})`.
Rendering it in the panel is a tiny follow-up; the event is published now so the
data is available.

## Error handling

- All ambient calls are null-safe: `mark`/`end_turn` with no active timeline do
  nothing. Instrumentation must never break a turn — `end_turn` swallows its own
  exceptions around logging/emit.
- `clock` injection makes tests deterministic; production uses `perf_counter`.

## Testing (TDD, CI-safe)

Pure-logic tests for `Timeline`: marks recorded once, deltas ordered, `total_ms`,
`summary` format, out-of-order safety. Ambient-API tests: `mark` is a no-op with no
active turn; `start_turn`/`mark`/`end_turn` roundtrip; thread isolation (two threads
keep separate timelines). No mic/model/network — fully CI-safe.

## Rollout

Behavior-neutral; ships dark (just logs + one HUD event). Establishes the baseline
the rest of v3.5 is measured against.
