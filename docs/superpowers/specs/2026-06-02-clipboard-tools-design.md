# Clipboard Tools — Design (v3.4 Layer 2)

**Date:** 2026-06-02
**Status:** Proposed
**Milestone:** v3.4 "Agent Capabilities" — Layer 2 (first capability tool)
**Branch:** `feature/clipboard-tools` (stacked on `feature/routing-unification`, PR #6)

---

## Problem / Goal

Give the tool agent read/write access to the system clipboard — the first v3.4
**Layer-2 capability tool**. After the Layer-1 foundation (registry + `@tool` +
plugin loader) and the routing unification (the registry is now the single source
of truth), adding a capability is just "register one or more `@tool`s, and
optionally a keyword fast-path phrase." Clipboard is the cheapest, highest-value
starter: `pyperclip` is already importable (it rides in transitively via
PyAutoGUI), so there is no real install burden.

## Goals

- Two registry tools — `read_clipboard`, `write_clipboard` — that **return** a
  string (no `speak`), following the existing `core/agent/builtins.py` pattern.
- `read_clipboard` reachable via the **instant keyword fast-path**; **both** tools
  reachable via the LLM agent (automatic once registered).
- **Lean / free / local:** pin the already-present `pyperclip`; no functional
  install burden, no paid services, no new heavy dependency.
- All tests **CI-safe** (monkeypatch `pyperclip`; never touch a real clipboard).

## Non-goals

- No clear-clipboard, no image/file clipboard, no `write_clipboard` keyword path,
  no `ACTION_VERBS` changes, no clipboard history.
- Not a release; no version bump (Release Drafter accumulates it under v3.4).

---

## Design

### Dependency

`pyperclip` (1.11.0) is currently present **only transitively** (PyAutoGUI →
mouseinfo → pyperclip). Since we now depend on it directly, **pin it explicitly**
in `requirements.txt`:

```
# Clipboard
pyperclip==1.11.0
```

It is pure-Python, free, and cross-platform. **Importing** it is CI-safe (no
display needed). At runtime on Linux it needs an `xclip`/`xsel` backend, but the
tests monkeypatch it, so CI never invokes a real clipboard. Windows uses the
native backend at runtime.

### New `@tool`s in `core/agent/builtins.py`

Add `import pyperclip` at module top and a module constant
`CLIPBOARD_PREVIEW_LIMIT = 200`.

**`read_clipboard()`** — no params:

```python
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
```

- Empty / whitespace-only / non-text clipboard (where `paste()` returns `""` on
  Windows for an image or file) → `"The clipboard is empty."`
- `<= 200` chars → the text **verbatim** (spoken in full).
- `> 200` chars → a length report + a 200-char ASCII-`...`-truncated preview.

**`write_clipboard(text)`** — required `str` param `text`:

```python
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

Returns a fixed confirmation — it deliberately does **not** echo the (possibly
long/arbitrary) copied text, consistent with the read-truncation philosophy.

### Routing — keyword fast-path (`core/router/intent_router.py`)

Add a read-specific phrase tuple and a branch to `resolve_keyword_tool` that
returns `ToolCall("read_clipboard", {})`:

```python
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

```python
    if any(p in query for p in _CLIPBOARD_READ):

        return ToolCall("read_clipboard", {})
```

These phrases are **read-specific**, so a copy command (`"copy hello to the
clipboard"`) matches **none** of them → the resolver returns `None` → the query
falls through to the LLM tool agent, which maps it to `write_clipboard` (the
phrase contains "clipboard", so `decide_tool`'s registry-name word-gate passes it
and the LLM fills the `text` arg).

`write_clipboard` has **no keyword path** — the text to copy is arbitrary and
cannot be deterministically extracted by substring rules.

### Behavior summary

| Utterance | Path | Result |
|---|---|---|
| `"what's on my clipboard"` | keyword (instant) | `read_clipboard` |
| `"read my clipboard"` | keyword (instant) | `read_clipboard` |
| `"copy hello world to the clipboard"` | LLM agent | `write_clipboard{text:"hello world"}` |
| clipboard empty / holds an image | — | `"The clipboard is empty."` |
| clipboard holds a 3000-char blob | — | length + 200-char truncated preview |

### Error handling

No new try/except: `execute_tool` already wraps handler exceptions (logs +
returns `"Tool execution failed."`), so a `pyperclip` backend failure degrades
gracefully.

---

## Testing (all CI-safe, monkeypatched — no real clipboard)

**`tests/test_clipboard.py`** (patch `agent_builtins.pyperclip`):

- `read_clipboard` empty: `paste -> ""` → `"The clipboard is empty."`
- `read_clipboard` whitespace: `paste -> "   "` → `"The clipboard is empty."`
- `read_clipboard` short: `paste -> "hello"` → `"hello"` (verbatim).
- `read_clipboard` long: `paste -> "x" * 3000` → asserts the result contains
  `"3000 characters"`, starts with `"Your clipboard has"`, and ends with
  `"(truncated)."`.
- `write_clipboard`: `copy` captured → arg equals the passed text; return equals
  `"Copied to clipboard."`.
- registration: `read_clipboard` and `write_clipboard` are in the registry after
  `loader.load_builtins()`.

**`tests/test_intent_router.py`** additions:

- Each phrase in `_CLIPBOARD_READ` → `ToolCall("read_clipboard", {})` (parametrized).
- `"copy hello to clipboard"` → `None` (correctly falls through to the LLM path).
- substring-in-sentence: `"hey jarvis what's on my clipboard please"` →
  `ToolCall("read_clipboard", {})`.

## Risks / mitigations

- **Transitive → explicit dep:** pinning `pyperclip` makes it first-class, so a
  future PyAutoGUI change that drops it won't break us.
- **Linux/CI clipboard backend:** tests monkeypatch `pyperclip`; CI never touches
  a real clipboard. Windows runtime uses the native backend.
- **`"clipboard"` substring greediness:** read phrases are multi-word and
  read-specific, so write commands don't match them — they correctly route to the
  LLM `write_clipboard`.
- **Long-text echo:** the 200-char truncation caps spoken output for `read`;
  `write` returns a fixed confirmation with no echo.

## Out of scope

- `clear_clipboard`, image/file clipboard, a `write_clipboard` keyword path,
  adding `"copy "`/`"paste "` to `ACTION_VERBS`, clipboard history.
