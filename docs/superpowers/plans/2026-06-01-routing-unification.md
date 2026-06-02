# Routing Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the tool registry the single source of truth for OS actions by routing the fast keyword path and the LLM path through one backend, eliminating the parallel `core/intents` + `core/commands` + `core/automation` stack.

**Architecture:** `app.process_query` calls `resolve_keyword_tool(query)` (instant, deterministic, no LLM) and falls back to `decide_tool(query)` (LLM) only on a miss. Both return a `registry.ToolCall` and converge on `execute_tool`. The keyword resolver is rewritten to emit `ToolCall`s instead of dispatching handlers; three new `@tool`s (`close_app`, `system_status`, `search_web`) give the registry the actions that previously lived only in the keyword backend, which is then deleted.

**Tech Stack:** Python 3.11, stdlib (`subprocess`, `webbrowser`, `urllib.parse`), `psutil`, `pytest` with `monkeypatch`. No new dependencies.

**Source of truth:** [docs/superpowers/specs/2026-06-01-routing-unification-design.md](../specs/2026-06-01-routing-unification-design.md) (audit finding A1).

---

## File Structure

**Created:**
- `tests/test_builtins_actions.py` — unit tests for the three new registry tools (`close_app`, `system_status`, `search_web`), all monkeypatched so no real side effects fire in CI.

**Modified:**
- `core/agent/builtins.py` — add `import psutil` + `import urllib.parse`; add `resolve_close_image()` helper and the three new `@tool`s. Existing tools unchanged.
- `core/router/intent_router.py` — replace `route_intent(query) -> handler` with `resolve_keyword_tool(query) -> ToolCall | None`. Becomes a pure, stdlib + registry module with no `core.intents` imports.
- `app.py` — swap the import `route_intent` → `resolve_keyword_tool`; delete `_run_intent_handler`; replace the handler-dispatch block in `process_query` with the unified resolver-then-LLM flow.
- `tests/test_intent_router.py` — rewrite to assert `resolve_keyword_tool` returns the correct `ToolCall` per the parity table, and `None` for non-actions.
- `tests/test_process_query.py` — replace `test_routes_to_intent_handler`; fix the `app.route_intent` monkeypatch in `test_llm_fallback_saves_memory`; add a keyword-miss-falls-through test.

**Deleted (the parallel backend — verified no remaining importers after the rewrite):**
- `core/intents/app_control.py`, `core/intents/media_control.py`, `core/intents/system_status.py`, `core/intents/browser.py`
- `core/commands/handlers.py` (empties the `core/commands/` package — no `__init__.py` exists)
- `core/automation/system.py` (empties the `core/automation/` package — no `__init__.py` exists)

---

## Task 1: Add `close_app`, `system_status`, `search_web` registry tools

Add the three actions that previously lived only in the keyword backend (`closeApp`, `condition`, two-step Google search) to the tool registry, refactored to **return** a string instead of calling `speak`. Done first so the resolver's target tools exist before routing changes.

**Files:**
- Modify: `core/agent/builtins.py`
- Test: `tests/test_builtins_actions.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_builtins_actions.py`:

```python
from core.agent import builtins as agent_builtins
from core.agent import registry


# --- close_app -------------------------------------------------------------

def test_resolve_close_image_known():
    assert agent_builtins.resolve_close_image("Calculator") == "calc.exe"
    assert agent_builtins.resolve_close_image("notepad") == "notepad.exe"
    assert agent_builtins.resolve_close_image("paint") == "mspaint.exe"


def test_resolve_close_image_passthrough():
    assert agent_builtins.resolve_close_image("vlc") == "vlc.exe"
    assert agent_builtins.resolve_close_image("foo.exe") == "foo.exe"


def test_close_app_runs_taskkill(monkeypatch):
    calls = []

    def _fake_run(cmd, check=True):
        calls.append((cmd, check))

    monkeypatch.setattr(agent_builtins.subprocess, "run", _fake_run)
    out = agent_builtins.close_app("notepad")
    assert calls == [(["taskkill", "/f", "/im", "notepad.exe"], False)]
    assert out == "Closing notepad."


# --- system_status ---------------------------------------------------------

def test_system_status_with_battery(monkeypatch):
    class _Batt:
        percent = 80
        power_plugged = True

    monkeypatch.setattr(agent_builtins.psutil, "cpu_percent",
                        lambda interval=0: 42.0)
    monkeypatch.setattr(agent_builtins.psutil, "sensors_battery",
                        lambda: _Batt())
    out = agent_builtins.system_status()
    assert out == "CPU at 42 percent, battery 80 percent, charging."


def test_system_status_no_battery(monkeypatch):
    monkeypatch.setattr(agent_builtins.psutil, "cpu_percent",
                        lambda interval=0: 42.0)
    monkeypatch.setattr(agent_builtins.psutil, "sensors_battery",
                        lambda: None)
    out = agent_builtins.system_status()
    assert out == "CPU at 42 percent."


# --- search_web ------------------------------------------------------------

def test_search_web_opens_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(agent_builtins.webbrowser, "open",
                        lambda url: opened.append(url))
    out = agent_builtins.search_web("funny cats")
    assert opened == ["https://www.google.com/search?q=funny+cats"]
    assert out == "Searching the web for funny cats."


# --- registration ----------------------------------------------------------

def test_new_tools_registered():
    from core.agent import loader
    loader.load_builtins()
    for name in ("close_app", "system_status", "search_web"):
        assert registry.get(name) is not None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_builtins_actions.py -v`
Expected: FAIL — `AttributeError: module 'core.agent.builtins' has no attribute 'resolve_close_image'` (and the `@tool` functions don't exist yet).

- [ ] **Step 3: Update the builtins import block**

In `core/agent/builtins.py`, change the top imports from:

```python
import os

import subprocess

import webbrowser

from core.agent.registry import (
    tool
)
```

to:

```python
import os

import subprocess

import urllib.parse

import webbrowser

import psutil

from core.agent.registry import (
    tool
)
```

- [ ] **Step 4: Add the close-image resolver and the three tools**

Append to the end of `core/agent/builtins.py`:

```python
_CLOSE_IMAGES = {
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
}


def resolve_close_image(name):

    key = name.strip().lower()

    if key in _CLOSE_IMAGES:

        return _CLOSE_IMAGES[key]

    return key if key.endswith(".exe") else f"{key}.exe"


@tool(
    "close_app",
    "Close a running Windows application by name (e.g. notepad, calculator, paint)",
    params={
        "name": {
            "type": "str",
            "required": True,
            "desc": "the app to close, e.g. notepad",
        }
    },
)
def close_app(name):

    image = resolve_close_image(name)

    # subprocess.run (not os.system) per the audit's hardening note; check=False
    # so "no such process" never raises (target may already be closed).
    subprocess.run(["taskkill", "/f", "/im", image], check=False)

    return f"Closing {name}."


@tool("system_status", "Report CPU usage and battery status")
def system_status():

    cpu = psutil.cpu_percent(interval=0.3)

    battery = psutil.sensors_battery()

    if battery is None:

        return f"CPU at {cpu:.0f} percent."

    pct = battery.percent

    charging = "charging" if battery.power_plugged else "on battery"

    return (
        f"CPU at {cpu:.0f} percent, "
        f"battery {pct:.0f} percent, {charging}."
    )


@tool(
    "search_web",
    "Search the web for a query in the browser",
    params={
        "query": {
            "type": "str",
            "required": True,
            "desc": "what to search for, e.g. weather today",
        }
    },
)
def search_web(query):

    url = (
        "https://www.google.com/search?q="
        + urllib.parse.quote_plus(query)
    )

    webbrowser.open(url)

    return f"Searching the web for {query}."
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_builtins_actions.py tests/test_open_app.py -v`
Expected: PASS (all new tests green; `test_open_app.py` still green — existing tools untouched).

- [ ] **Step 6: Commit**

```bash
git add core/agent/builtins.py tests/test_builtins_actions.py
git commit -m "feat(agent): close_app, system_status, search_web registry tools

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Unify routing (resolver + app.py rewire)

Rewrite `route_intent` into `resolve_keyword_tool` (returns a `ToolCall`), then rewire `process_query` to use it. These land together: renaming `route_intent` breaks `app.py`'s import, so the suite is only green once both are done.

**Files:**
- Modify: `core/router/intent_router.py`
- Modify: `app.py:53-55` (import), `app.py:105-113` (delete `_run_intent_handler`), `app.py:153-188` (routing block)
- Test: `tests/test_intent_router.py` (rewrite), `tests/test_process_query.py` (update)

- [ ] **Step 1: Rewrite the intent-router test**

Replace the entire contents of `tests/test_intent_router.py` with:

```python
import pytest

from core.router.intent_router import resolve_keyword_tool
from core.agent.registry import ToolCall


@pytest.mark.parametrize("query,expected", [
    ("open calculator", ToolCall("open_app", {"name": "calculator"})),
    ("open notepad", ToolCall("open_app", {"name": "notepad"})),
    ("open paint", ToolCall("open_app", {"name": "paint"})),
    ("open edge", ToolCall("open_app", {"name": "edge"})),
    ("open google", ToolCall("open_google", {})),
    ("close calculator", ToolCall("close_app", {"name": "calculator"})),
    ("close notepad", ToolCall("close_app", {"name": "notepad"})),
    ("close paint", ToolCall("close_app", {"name": "paint"})),
    ("volume up", ToolCall("increase_volume", {})),
    ("increase volume", ToolCall("increase_volume", {})),
    ("increase the volume", ToolCall("increase_volume", {})),
    ("raise the volume", ToolCall("increase_volume", {})),
    ("volume down", ToolCall("decrease_volume", {})),
    ("decrease the volume", ToolCall("decrease_volume", {})),
    ("lower volume", ToolCall("decrease_volume", {})),
    ("mute", ToolCall("mute_volume", {})),
    ("volume mute", ToolCall("mute_volume", {})),
    ("system status", ToolCall("system_status", {})),
    ("system info", ToolCall("system_status", {})),
    ("cpu usage", ToolCall("system_status", {})),
    ("battery level", ToolCall("system_status", {})),
    ("battery percentage", ToolCall("system_status", {})),
    ("search google for cats", ToolCall("search_web", {"query": "cats"})),
    ("search the web for cats", ToolCall("search_web", {"query": "cats"})),
    ("search for cats", ToolCall("search_web", {"query": "cats"})),
    ("google cats", ToolCall("search_web", {"query": "cats"})),
])
def test_resolve_returns_expected_toolcall(query, expected):
    assert resolve_keyword_tool(query) == expected


def test_substring_match_inside_a_sentence_still_routes():
    # Substring containment is preserved for the open/close/volume commands.
    assert resolve_keyword_tool("hey can you open notepad for me") == \
        ToolCall("open_app", {"name": "notepad"})


def test_open_google_is_homepage_not_search():
    # "open google" must beat the search triggers -> homepage, not a web search.
    assert resolve_keyword_tool("open google") == ToolCall("open_google", {})


def test_bare_google_with_no_term_is_not_a_search():
    # "google" with nothing after it is not a command; fall through to the LLM.
    assert resolve_keyword_tool("google") is None


def test_unmatched_query_returns_none():
    # Falls through to the LLM tool agent / chat in the real pipeline.
    for query in ("what is python", "tell me a joke", "open spotify"):
        assert resolve_keyword_tool(query) is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_intent_router.py -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_keyword_tool' from 'core.router.intent_router'`.

- [ ] **Step 3: Rewrite the intent router**

Replace the entire contents of `core/router/intent_router.py` with:

```python
from core.agent.registry import ToolCall


_OPEN_APPS = {
    "open calculator": "calculator",
    "open notepad": "notepad",
    "open paint": "paint",
    "open edge": "edge",
}

_CLOSE_APPS = {
    "close calculator": "calculator",
    "close notepad": "notepad",
    "close paint": "paint",
}

_INCREASE_VOLUME = (
    "volume up",
    "increase volume",
    "increase the volume",
    "raise volume",
    "raise the volume",
)

_DECREASE_VOLUME = (
    "volume down",
    "decrease volume",
    "decrease the volume",
    "lower volume",
    "lower the volume",
)

_SYSTEM_STATUS = (
    "system status",
    "system condition",
    "condition of the system",
    "system info",
    "system information",
    "cpu usage",
    "battery status",
    "battery level",
    "battery percentage",
)

# Ordered: "search google for " before "google " so the longer, more specific
# trigger wins (otherwise "google " would swallow it and mis-extract the term).
_SEARCH_TRIGGERS = (
    "search google for ",
    "search the web for ",
    "search for ",
    "google ",
)


def resolve_keyword_tool(query):
    """Map a known command phrase to a registry ToolCall, or None.

    Deterministic, LLM-free, stdlib + registry only (importable in CI). This is
    the fast path: common voice commands resolve here without paying Ollama
    latency. A miss returns None and the caller falls back to the LLM tool
    agent. Open/close/volume/status use substring containment (so an embedded
    keyword in a longer sentence still matches); web search uses prefix
    extraction so the search term can be pulled off the trigger phrase.
    """

    # Open apps.
    for phrase, name in _OPEN_APPS.items():

        if phrase in query:

            return ToolCall("open_app", {"name": name})

    # Open Google homepage. Checked before the search triggers so "open google"
    # opens the homepage instead of being parsed as a web search.
    if "open google" in query:

        return ToolCall("open_google", {})

    # Close apps.
    for phrase, name in _CLOSE_APPS.items():

        if phrase in query:

            return ToolCall("close_app", {"name": name})

    # Volume.
    if any(p in query for p in _INCREASE_VOLUME):

        return ToolCall("increase_volume", {})

    if any(p in query for p in _DECREASE_VOLUME):

        return ToolCall("decrease_volume", {})

    if "mute" in query:

        return ToolCall("mute_volume", {})

    # System status.
    if any(p in query for p in _SYSTEM_STATUS):

        return ToolCall("system_status", {})

    # Web search: strip the trigger prefix to get the search term.
    for trigger in _SEARCH_TRIGGERS:

        if query.startswith(trigger):

            term = query[len(trigger):].strip()

            if term:

                return ToolCall("search_web", {"query": term})

    return None
```

- [ ] **Step 4: Run the router test to verify it passes**

Run: `python -m pytest tests/test_intent_router.py -v`
Expected: PASS (all parity cases green). Note: the full suite is still RED at this point — `app.py` still imports `route_intent`. Fixed in the next steps.

- [ ] **Step 5: Update the process_query test**

In `tests/test_process_query.py`, add this import at the top (after `import app`):

```python
from core.agent.registry import ToolCall
```

Replace `test_routes_to_intent_handler` (the whole function) with:

```python
def test_fast_path_resolves_and_executes_tool(monkeypatch):
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    monkeypatch.setattr(app, "parse_reminder", lambda q: None)
    monkeypatch.setattr(app, "resolve_keyword_tool",
                        lambda q: ToolCall("increase_volume", {}))

    # The LLM path must NOT run on a keyword hit.
    def _boom(q):
        raise AssertionError("decide_tool should not run on a keyword hit")

    monkeypatch.setattr(app, "decide_tool", _boom)

    ran = {}

    def _fake_execute(call):
        ran["call"] = call
        return "Increasing volume."

    monkeypatch.setattr(app, "execute_tool", _fake_execute)
    spoken = []
    monkeypatch.setattr(app, "speak", lambda t: spoken.append(t))

    app.process_query("volume up", _FakeTaskManager())
    assert ran["call"] == ToolCall("increase_volume", {})
    assert spoken == ["Increasing volume."]


def test_keyword_miss_falls_through_to_llm_tool_agent(monkeypatch):
    monkeypatch.setattr(app, "extract_personal_info", lambda q: None)
    monkeypatch.setattr(app, "parse_reminder", lambda q: None)
    monkeypatch.setattr(app, "resolve_keyword_tool", lambda q: None)
    monkeypatch.setattr(app, "decide_tool",
                        lambda q: ToolCall("open_app", {"name": "spotify"}))

    ran = {}

    def _fake_execute(call):
        ran["call"] = call
        return "Opening spotify."

    monkeypatch.setattr(app, "execute_tool", _fake_execute)
    monkeypatch.setattr(app, "speak", lambda t: None)

    app.process_query("open spotify", _FakeTaskManager())
    assert ran["call"] == ToolCall("open_app", {"name": "spotify"})
```

In the same file, in `test_llm_fallback_saves_memory`, change the line:

```python
    monkeypatch.setattr(app, "route_intent", lambda q: None)
```

to:

```python
    monkeypatch.setattr(app, "resolve_keyword_tool", lambda q: None)
```

- [ ] **Step 6: Run the process_query test to verify it fails**

Run: `python -m pytest tests/test_process_query.py -v`
Expected: FAIL — importing `app` still pulls `route_intent` (gone) and `app.resolve_keyword_tool` doesn't exist yet. Fixed next.

- [ ] **Step 7: Swap the app.py import**

In `app.py`, change:

```python
from core.router.intent_router import (
    route_intent
)
```

to:

```python
from core.router.intent_router import (
    resolve_keyword_tool
)
```

- [ ] **Step 8: Delete `_run_intent_handler`**

In `app.py`, delete this function entirely (currently lines 105-113):

```python
def _run_intent_handler(handler, query):

    if handler.__name__ == "handle_browser":

        handler(query, speak, command)

    else:

        handler(query, speak)
```

- [ ] **Step 9: Replace the routing block in process_query**

In `app.py:process_query`, replace this block (currently lines 153-188):

```python
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

    call = decide_tool(query)

    if call is not None:

        logger.info(f"Executed Tool: {call.name} args={call.args}")

        response = execute_tool(call)

        if response:

            speak(response)

        return
```

with:

```python
    call = resolve_keyword_tool(query)

    if call is None:

        # Only the LLM path needs "thinking" — the keyword path is instant.
        events.emit("state", state="thinking")

        call = decide_tool(query)

    if call is not None:

        logger.info(f"Executed Tool: {call.name} args={call.args}")

        response = execute_tool(call)

        if response:

            speak(response)

        return
```

- [ ] **Step 10: Run the full suite to verify it passes**

Run: `python -m pytest -v`
Expected: PASS — all tests green (router, process_query, builtins, and every pre-existing test). The parallel backend files still exist but are now unimported; they are removed in Task 3.

- [ ] **Step 11: Commit**

```bash
git add core/router/intent_router.py app.py tests/test_intent_router.py tests/test_process_query.py
git commit -m "refactor(router): unify routing on resolve_keyword_tool -> ToolCall

route_intent now returns a registry ToolCall instead of dispatching a
handler; process_query runs the keyword path then the LLM path through one
execute_tool. Fixes audit A1 (keyword router shadowing registry tools).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Delete the parallel backend

Remove the now-dead handler stack. No module imports these after Task 2 (verified: only `intent_router` imported the intents, only the intents imported `automation.system` / `commands.handlers`, and `test_intent_router` was rewritten).

**Files:**
- Delete: `core/intents/app_control.py`, `core/intents/media_control.py`, `core/intents/system_status.py`, `core/intents/browser.py`
- Delete: `core/commands/handlers.py`
- Delete: `core/automation/system.py`

- [ ] **Step 1: Confirm there are no remaining importers**

Run: `git grep -n -E "core\.(automation|commands|intents)|route_intent|_run_intent_handler" -- "*.py"`
Expected: **no output** (empty). If anything prints, stop and fix that reference before deleting.

- [ ] **Step 2: Remove the files**

```bash
git rm core/intents/app_control.py core/intents/media_control.py core/intents/system_status.py core/intents/browser.py
git rm core/commands/handlers.py
git rm core/automation/system.py
```

(These empty the `core/commands/` and `core/automation/` packages — neither has an `__init__.py`, so the now-empty directories simply disappear from the tree.)

- [ ] **Step 3: Run the full suite**

Run: `python -m pytest -v`
Expected: PASS — same green result as Task 2 Step 10 (nothing imported the deleted files).

- [ ] **Step 4: Run build-breaking lint**

Run: `python -m flake8 . --select=E9,F63,F7,F82,F401 --exclude=venv,__pycache__,dist,build --count`
Expected: `0` (no unused-import / syntax errors introduced; the deleted imports are gone).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(router): delete the parallel intents/commands/automation backend

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Final verification and doc status

Confirm the whole change is green and clean, and flip the spec status to Implemented.

**Files:**
- Modify: `docs/superpowers/specs/2026-06-01-routing-unification-design.md` (status line)

- [ ] **Step 1: Mark the spec implemented**

In `docs/superpowers/specs/2026-06-01-routing-unification-design.md`, change:

```markdown
**Status:** Proposed
```

to:

```markdown
**Status:** Implemented (2026-06-02)
```

- [ ] **Step 2: Run the full quality gate**

Run both:

```bash
python -m pytest -v
python -m flake8 . --select=E9,F63,F7,F82,F401 --exclude=venv,__pycache__,dist,build --count
```

Expected: pytest all PASS; flake8 prints `0`.

- [ ] **Step 3: Run the quality-warning lint (non-blocking, informational)**

Run: `python -m flake8 . --exit-zero --max-complexity=10 --max-line-length=127 --exclude=venv,__pycache__,dist,build`
Expected: no new warnings attributable to the changed files (`intent_router.py`, `builtins.py`, `app.py`). `--exit-zero` never fails the gate; this is a hygiene read.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-06-01-routing-unification-design.md
git commit -m "docs(spec): mark routing unification implemented

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 5: Finish the branch**

Use the `superpowers:finishing-a-development-branch` skill to choose how to integrate `feature/routing-unification` (PR to `main`, with a Release-Drafter `feature` label so it accumulates under v3.4 — no version bump, per the spec's non-goals).

---

## Self-Review

**1. Spec coverage** — every spec section maps to a task:

| Spec item | Task |
|---|---|
| `resolve_keyword_tool` returns `ToolCall \| None` | Task 2, Step 3 |
| Phrase → ToolCall parity table | Task 2, Step 1 (tests) + Step 3 (impl) |
| `open edge` dead-route fix | Task 2 (`_OPEN_APPS["open edge"] -> open_app{edge}`) + `test_resolve_returns_expected_toolcall` |
| `open google` = homepage, not 2-step search | Task 2 (`open_google` checked before search triggers) + `test_open_google_is_homepage_not_search` |
| `search_web` deterministic prefix extraction | Task 2 (`_SEARCH_TRIGGERS` strip) + parametrized search tests |
| New `close_app` tool | Task 1 |
| New `system_status` tool (return, not speak) | Task 1 |
| New `search_web` tool | Task 1 |
| `process_query` resolver-then-LLM flow, single `execute_tool` | Task 2, Step 9 |
| Delete intents/commands/automation | Task 3 |
| Remove `_run_intent_handler` + import swap | Task 2, Steps 7-8 |
| Volume stays 5× everywhere | Inherited — resolver targets the unchanged `increase/decrease/mute_volume` tools |
| `open_calculator` kept (out of scope to remove) | Untouched by all tasks |
| Tests all CI-safe (no mic/display/network/model) | Tasks 1-2 monkeypatch `subprocess`/`psutil`/`webbrowser`/`execute_tool`/`decide_tool` |
| Existing `test_open_app.py` / `test_tool_executor.py` / `test_registry.py` valid | Untouched; re-run in Task 2 Step 10 |

**2. Placeholder scan** — no TBD/TODO/"add error handling"/"similar to Task N". Every code step shows complete code; every run step shows the exact command and expected result.

**3. Type consistency** — `resolve_keyword_tool` returns `registry.ToolCall` (frozen dataclass, value-equality) consistently across the router impl (Task 2 Step 3), the router tests (Step 1), and the process_query tests (Step 5). `close_app(name)`, `system_status()`, `search_web(query)` signatures match between the impl (Task 1 Step 4), their `@tool` param specs, and the tests (Task 1 Step 1). `resolve_close_image` is defined in Task 1 Step 4 and used by `close_app` + tested in the same task. The `subprocess.run(cmd, check=False)` call shape matches the test's `_fake_run(cmd, check=True)` capture.

**Note on commit-boundary greenness:** Task 2 deliberately bundles the router rewrite and the `app.py` rewire into one commit because renaming `route_intent` breaks `app.py`'s import — the suite is red between Step 3 and Step 9 but green at the Step 11 commit. This is called out in Steps 4 and 6 so an executor doesn't commit early.
