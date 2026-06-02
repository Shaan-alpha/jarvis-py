# Routing Unification — Design (v3.4)

**Date:** 2026-06-01
**Status:** Implemented (2026-06-02)
**Audit finding:** A1 (keyword router shadows registry builtin tools)

---

## Problem

`app.py:process_query` routes an action query through **two parallel backends**:

1. The keyword `core/router/intent_router.py` → handlers in `core/intents/*` →
   `core/automation/system.py` / `core/commands/handlers.py`.
2. The LLM tool agent `core/agent/tool_agent.decide_tool` → registry `@tool`s in
   `core/agent/builtins.py` → `tool_executor.execute_tool`.

The keyword router runs **first**, so for the exact phrases it knows it **shadows**
the registry tools `open_calculator`, `open_google`, `increase_volume`,
`decrease_volume`, `mute_volume` — those tools can essentially never fire. Two
implementations exist for the same actions (e.g. volume: a one-press handler **and**
a five-press tool), and several actions live in only one backend:

- `close_app` (calc/notepad/paint via `taskkill`) and `system_status` (CPU/battery)
  exist **only** as keyword handlers — the LLM agent cannot invoke them.
- `"open edge"` is a **dead route**: the router sends it to the browser handler, but
  `browsing()` only handles `"google"`, so `"open edge"` does nothing (even though
  `open_app` has an `edge` alias).
- `"open google"` is a **two-step interactive voice search** (prompt → second mic
  capture → open results), not a homepage open.

## Goals

- One implementation per action (single source of truth = the tool registry).
- Eliminate the shadowing and the duplicate/dead code.
- Preserve the **instant, deterministic, Ollama-free fast path** for known commands
  (works offline and online, zero LLM latency).
- Make every action **LLM-accessible** as a side effect (the agent gains close-app,
  system-status, and web-search).
- All tests stay CI-safe (no mic/display/network/model).

## Non-goals

- No change to wake word, STT, TTS, memory, reminders, or LLM chat fallback.
- No new dependencies. No arg-clarification loop. No tool sandbox.
- Not a release; no version bump (Release Drafter accumulates it under v3.4).

---

## Design

### Routing flow (`process_query`)

```
profile capture → reminder            (unchanged)
↓
call = resolve_keyword_tool(query)     # instant, deterministic, no LLM
       or decide_tool(query)           # LLM fallback, only if keyword misses
↓
if call is not None:
    response = execute_tool(call)
    if response: speak(response)
    return
↓
ask_llm(query)                         # chat fallback (unchanged)
```

Both paths converge on `execute_tool` + the registry. The keyword path
short-circuits (`or`), so common commands never depend on Ollama or pay phi3
latency. `decide_tool` keeps its existing registry-aware action gate.

### `core/router/intent_router.py` → keyword→ToolCall resolver

Rename `route_intent(query) -> handler` to `resolve_keyword_tool(query) -> ToolCall | None`.
It keeps its phrase tables (substring match, first match wins) but returns a
`registry.ToolCall(name, args)`. Pure, stdlib-only, no LLM, importable in CI.

**Phrase → ToolCall parity table:**

| Phrase(s) | ToolCall |
|---|---|
| `open calculator` | `open_app{name:"calculator"}` |
| `open notepad` | `open_app{name:"notepad"}` |
| `open paint` | `open_app{name:"paint"}` |
| `open edge` | `open_app{name:"edge"}`  *(fixes dead route)* |
| `open google` | `open_google{}`  *(homepage)* |
| `close calculator` / `close notepad` / `close paint` | `close_app{name:...}` |
| `volume up` / `increase (the) volume` / `raise (the) volume` | `increase_volume{}` |
| `volume down` / `decrease (the) volume` / `lower volume` | `decrease_volume{}` |
| `mute` / `mute volume` / `volume mute` | `mute_volume{}` |
| `search google for X` / `google X` / `search (the web) for X` | `search_web{query:"X"}` |
| `system status/condition/info`, `cpu usage`, `battery status/level/percentage` | `system_status{}` |

Query extraction for `search_web` is deterministic prefix-stripping of the trigger
phrase (e.g. `"search google for cats"` → `"cats"`).

### New `@tool`s in `core/agent/builtins.py`

- **`close_app(name)`** — resolves `name` to a Windows image (`calculator→calc.exe`,
  `notepad→notepad.exe`, `paint→mspaint.exe`; folds in legacy `closeApp`) and runs
  `subprocess.run(["taskkill", "/f", "/im", image], check=False)`. Uses `subprocess`
  (not `os.system`) for consistency + the audit's hardening note. Returns
  `"Closing {name}."`
- **`system_status()`** — returns the CPU/battery string (moved verbatim from
  `core/automation/system.condition`, refactored to **return** instead of `speak`).
- **`search_web(query)`** — `webbrowser.open("https://www.google.com/search?q=" +
  urllib.parse.quote_plus(query))`; returns `"Searching the web for {query}."`

Volume/open tools are unchanged (volume stays **5×** per decision). `open_calculator`
is now redundant with `open_app{name:"calculator"}`; it is kept (harmless, explicit,
LLM-discoverable) — removal is optional and out of scope.

### Deletions (the parallel backend)

- `core/intents/app_control.py`, `media_control.py`, `system_status.py`, `browser.py`
- `core/commands/handlers.py` (and the now-empty `core/commands/` package)
- `core/automation/system.py` (`openApp` already exists as tools; `closeApp` +
  `condition` move to builtins) (and the now-empty `core/automation/` package)
- `app.py`: remove `_run_intent_handler` and the handler-dispatch block; drop the
  `route_intent` import, add `resolve_keyword_tool`. (`command` STT import stays —
  still used by the voice loop.)

No other modules import the deleted files (verified: only `intent_router` imports the
intents; only the intents import `automation.system` / `commands.handlers`).

---

## Behavior preservation

- Known commands: same outcome, same instant/offline path — now via one tool impl.
- `"open edge"`: **now works** (was a no-op).
- Volume: now **5×** everywhere (was 1× on the keyword path) — accepted.
- Google: **one-shot** `"search google for X"` replaces the two-step prompt → mic
  capture flow (accepted); bare `"open google"` opens the homepage.
- New: the LLM agent can now also close apps, report system status, and search.

## Testing (all CI-safe)

- `tests/test_intent_router.py` — rewrite to assert `resolve_keyword_tool` returns the
  right `ToolCall(name, args)` per the parity table, and `None` for non-actions.
- `tests/test_process_query.py` — update `test_routes_to_intent_handler` to assert the
  fast path produces a `ToolCall` and `execute_tool` runs it.
- New builtin-tool tests (monkeypatched, no real side effects): `close_app`
  (patch `subprocess.run`), `system_status` (patch `psutil.cpu_percent` +
  `sensors_battery`), `search_web` (patch `webbrowser.open`).
- Existing `tests/test_open_app.py`, `test_tool_executor.py`, `test_registry.py`
  remain valid.

## Risks / mitigations

- **Resolver/`decide_tool` arg shape mismatch** → both go through
  `registry.coerce_and_validate`; resolver emits already-valid args.
- **`taskkill` on Win11 UWP Calculator** — legacy used `calc.exe`; behavior is
  preserved verbatim (not improved here).
- **Dropped two-step search UX** — intentional, per decision; single-utterance search
  is simpler and tool-friendly.

## Out of scope

- Removing the redundant `open_calculator` tool.
- WebSocket Origin/auth (S1), `_start_hud` complexity (A4), bool/float coercers (A3) —
  tracked separately.
