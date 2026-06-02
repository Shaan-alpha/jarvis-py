# Clipboard Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the tool agent read/write access to the system clipboard via two registry `@tool`s — the first v3.4 Layer-2 capability.

**Architecture:** Two `@tool`s in `core/agent/builtins.py` (`read_clipboard`, `write_clipboard`) backed by `pyperclip`, returning strings like every other builtin. `read_clipboard` also gets a keyword fast-path in `core/router/intent_router.py`; `write_clipboard` stays LLM-only (its text arg is arbitrary). `pyperclip` is pinned in `requirements.txt` (it was only present transitively via PyAutoGUI).

**Tech Stack:** Python 3.11, `pyperclip==1.11.0`, `pytest` + `monkeypatch`. No heavy/new dependency.

**Source of truth:** [docs/superpowers/specs/2026-06-02-clipboard-tools-design.md](../specs/2026-06-02-clipboard-tools-design.md).

**Branch:** `feature/clipboard-tools` (already cut, stacked on the now-merged routing unification; spec already committed here).

---

## File Structure

**Created:**
- `tests/test_clipboard.py` — unit tests for `read_clipboard` / `write_clipboard`, all monkeypatched (no real clipboard touched in CI).

**Modified:**
- `requirements.txt` — pin `pyperclip==1.11.0` (new explicit dep; was transitive).
- `core/agent/builtins.py` — add `import pyperclip`, a `CLIPBOARD_PREVIEW_LIMIT` constant, and the two `@tool`s. Existing tools unchanged.
- `core/router/intent_router.py` — add a `_CLIPBOARD_READ` phrase tuple and a branch in `resolve_keyword_tool` returning `ToolCall("read_clipboard", {})`.
- `tests/test_intent_router.py` — add clipboard-read routing tests (read phrases route; a copy command does not).

---

## Task 1: Clipboard `@tool`s + pin pyperclip

Add the two registry tools and pin the dependency. Done first so the tools exist before the resolver references `read_clipboard` in Task 2.

**Files:**
- Modify: `requirements.txt`
- Modify: `core/agent/builtins.py`
- Test: `tests/test_clipboard.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_clipboard.py`:

```python
from core.agent import builtins as agent_builtins
from core.agent import registry


def test_read_clipboard_empty(monkeypatch):
    monkeypatch.setattr(agent_builtins.pyperclip, "paste", lambda: "")
    assert agent_builtins.read_clipboard() == "The clipboard is empty."


def test_read_clipboard_whitespace(monkeypatch):
    monkeypatch.setattr(agent_builtins.pyperclip, "paste", lambda: "   ")
    assert agent_builtins.read_clipboard() == "The clipboard is empty."


def test_read_clipboard_short_returns_verbatim(monkeypatch):
    monkeypatch.setattr(agent_builtins.pyperclip, "paste", lambda: "hello")
    assert agent_builtins.read_clipboard() == "hello"


def test_read_clipboard_long_is_truncated(monkeypatch):
    monkeypatch.setattr(agent_builtins.pyperclip, "paste", lambda: "x" * 3000)
    out = agent_builtins.read_clipboard()
    assert out.startswith("Your clipboard has")
    assert "3000 characters" in out
    assert out.endswith("(truncated).")
    # Preview is capped at the limit, not the full 3000-char blob.
    assert len(out) < 300


def test_write_clipboard_copies_and_confirms(monkeypatch):
    copied = []
    monkeypatch.setattr(agent_builtins.pyperclip, "copy",
                        lambda t: copied.append(t))
    out = agent_builtins.write_clipboard("remember the milk")
    assert copied == ["remember the milk"]
    assert out == "Copied to clipboard."


def test_clipboard_tools_registered():
    from core.agent import loader
    loader.load_builtins()
    for name in ("read_clipboard", "write_clipboard"):
        assert registry.get(name) is not None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv\Scripts\python.exe -m pytest tests/test_clipboard.py -v`
Expected: FAIL — `AttributeError: module 'core.agent.builtins' has no attribute 'pyperclip'` (and `read_clipboard`/`write_clipboard` don't exist yet).

- [ ] **Step 3: Pin pyperclip in requirements.txt**

In `requirements.txt`, find the System-automation block:

```
# System automation
PyAutoGUI==0.9.54
psutil==7.2.2
```

Add a new section immediately after the `psutil==7.2.2` line (before the blank line and the Desktop-HUD section):

```
# System automation
PyAutoGUI==0.9.54
psutil==7.2.2

# Clipboard
pyperclip==1.11.0
```

- [ ] **Step 4: Add the `import pyperclip` to builtins**

In `core/agent/builtins.py`, change the top import block from:

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

to:

```python
import os

import subprocess

import urllib.parse

import webbrowser

import psutil

import pyperclip

from core.agent.registry import (
    tool
)
```

- [ ] **Step 5: Add the two clipboard tools**

Append to the end of `core/agent/builtins.py`:

```python
CLIPBOARD_PREVIEW_LIMIT = 200


@tool("read_clipboard", "Read the current text contents of the system clipboard")
def read_clipboard():

    text = pyperclip.paste()

    if not text or not text.strip():

        return "The clipboard is empty."

    if len(text) <= CLIPBOARD_PREVIEW_LIMIT:

        return text

    return (
        f"Your clipboard has {len(text)} characters. "
        f'It starts: "{text[:CLIPBOARD_PREVIEW_LIMIT]}..." (truncated).'
    )


@tool(
    "write_clipboard",
    "Copy the given text to the system clipboard",
    params={
        "text": {
            "type": "str",
            "required": True,
            "desc": "the text to copy to the clipboard",
        }
    },
)
def write_clipboard(text):

    pyperclip.copy(text)

    return "Copied to clipboard."
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/test_clipboard.py tests/test_open_app.py -v`
Expected: PASS (clipboard tests green; `test_open_app.py` still green — existing tools untouched).

- [ ] **Step 7: Commit**

```bash
git add requirements.txt core/agent/builtins.py tests/test_clipboard.py
git commit -m "feat(agent): clipboard read/write registry tools

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Keyword fast-path for `read_clipboard`

Let known "read my clipboard" phrases resolve instantly (no LLM), while a copy command correctly falls through to the LLM `write_clipboard`.

**Files:**
- Modify: `core/router/intent_router.py`
- Test: `tests/test_intent_router.py`

- [ ] **Step 1: Write the failing tests**

In `tests/test_intent_router.py`, add these three test functions at the end of the file (the module already imports `pytest`, `resolve_keyword_tool`, and `ToolCall`):

```python
@pytest.mark.parametrize("query", [
    "read clipboard",
    "read my clipboard",
    "what's on my clipboard",
    "what's in my clipboard",
    "what's on the clipboard",
    "check clipboard",
    "show clipboard",
])
def test_clipboard_read_phrases_route(query):
    assert resolve_keyword_tool(query) == ToolCall("read_clipboard", {})


def test_clipboard_read_substring_in_sentence():
    assert resolve_keyword_tool("hey jarvis what's on my clipboard please") == \
        ToolCall("read_clipboard", {})


def test_copy_command_is_not_a_clipboard_read():
    # "copy ... to clipboard" must fall through to the LLM (write_clipboard),
    # not match a read phrase.
    assert resolve_keyword_tool("copy hello to clipboard") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv\Scripts\python.exe -m pytest tests/test_intent_router.py -k clipboard -v`
Expected: FAIL — `read_clipboard` is not yet routed, so the read phrases return `None` instead of `ToolCall("read_clipboard", {})`.

- [ ] **Step 3: Add the `_CLIPBOARD_READ` phrase tuple**

In `core/router/intent_router.py`, find the `_SYSTEM_STATUS` tuple:

```python
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
```

Add this new tuple immediately after it (before `_SEARCH_TRIGGERS`):

```python
# Read-specific phrases. A "copy ... to clipboard" command matches NONE of these,
# so it falls through to the LLM write_clipboard (the resolver has no write path).
_CLIPBOARD_READ = (
    "read clipboard",
    "read my clipboard",
    "what's on my clipboard",
    "what's in my clipboard",
    "what's on the clipboard",
    "check clipboard",
    "show clipboard",
)
```

- [ ] **Step 4: Add the resolver branch**

In `core/router/intent_router.py`, inside `resolve_keyword_tool`, find the system-status branch:

```python
    # System status.
    if any(p in query for p in _SYSTEM_STATUS):

        return ToolCall("system_status", {})
```

Add the clipboard-read branch immediately after it (before the `# Web search` comment / `_SEARCH_TRIGGERS` loop):

```python
    # Read clipboard.
    if any(p in query for p in _CLIPBOARD_READ):

        return ToolCall("read_clipboard", {})
```

- [ ] **Step 5: Run the clipboard router tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/test_intent_router.py -k clipboard -v`
Expected: PASS (all 7 read phrases route; the substring sentence routes; the copy command returns `None`).

- [ ] **Step 6: Run the full suite + build-breaking lint**

Run:
```
venv\Scripts\python.exe -m pytest
venv\Scripts\python.exe -m flake8 . --select=E9,F63,F7,F82,F401 --exclude=venv,__pycache__,dist,build --count
```
Expected: pytest all PASS (the prior count + the new clipboard tests); flake8 prints `0`.

- [ ] **Step 7: Commit**

```bash
git add core/router/intent_router.py tests/test_intent_router.py
git commit -m "feat(router): keyword fast-path for read_clipboard

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 8: Finish the branch**

Use the `superpowers:finishing-a-development-branch` skill to open a PR for `feature/clipboard-tools` → `main` (Release-Drafter `enhancement` label, accumulates under v3.4; no version bump).

---

## Self-Review

**1. Spec coverage** — every spec item maps to a task:

| Spec item | Task |
|---|---|
| Pin `pyperclip==1.11.0` in requirements | Task 1, Step 3 |
| `import pyperclip` at module top | Task 1, Step 4 |
| `read_clipboard()` — empty/whitespace → "The clipboard is empty." | Task 1, Step 5 + `test_read_clipboard_empty`/`_whitespace` |
| `read_clipboard()` — ≤200 chars verbatim | Task 1, Step 5 + `test_read_clipboard_short_returns_verbatim` |
| `read_clipboard()` — >200 chars truncated preview (length + 200-char `...`) | Task 1, Step 5 + `test_read_clipboard_long_is_truncated` |
| `write_clipboard(text)` — copies + "Copied to clipboard." | Task 1, Step 5 + `test_write_clipboard_copies_and_confirms` |
| Both tools registered | Task 1 + `test_clipboard_tools_registered` |
| `read_clipboard` keyword fast-path (7 read phrases) | Task 2, Steps 3-4 + `test_clipboard_read_phrases_route` |
| Copy command falls through to LLM (no read match) | Task 2 + `test_copy_command_is_not_a_clipboard_read` |
| `write_clipboard` LLM-only (no keyword path) | Task 2 — only a read branch is added; no write branch |
| CI-safe tests (monkeypatch pyperclip) | Task 1 tests patch `agent_builtins.pyperclip.paste`/`copy` |
| Out of scope: clear/image/write-keyword/ACTION_VERBS | Not implemented — no task adds them |

**2. Placeholder scan** — no TBD/TODO/"add error handling"/"similar to Task N". Every code step shows complete code; every run step gives the exact command + expected result.

**3. Type consistency** — `read_clipboard()` (no args) and `write_clipboard(text)` signatures match between the impl (Task 1 Step 5), their `@tool` declarations, and the tests. `CLIPBOARD_PREVIEW_LIMIT` is defined once (Task 1 Step 5) and used in both the length check and the slice. `ToolCall("read_clipboard", {})` is the exact value the resolver returns (Task 2 Step 4) and the tests assert (Task 2 Step 1). The long-read return string ends with `"(truncated)."` — matching `test_read_clipboard_long_is_truncated`'s `endswith` assertion — and stays under 300 chars (≈38 + 200 + 15).
