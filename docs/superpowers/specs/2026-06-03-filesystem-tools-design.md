# File-system Tools — Design (v3.4 Layer 2)

**Date:** 2026-06-03
**Status:** Proposed
**Milestone:** v3.4 "Agent Capabilities" — Layer 2 (capability tools)
**Branch:** `feature/filesystem-tools` (off `main`)

---

## Problem / Goal

Give the tool agent the ability to **read, write, search, and list files** — the
next v3.4 Layer-2 capability after clipboard. A voice assistant that can stash a
note, read it back, and find it again is genuinely useful. The hazard is obvious:
voice STT mangles filenames, and an LLM-chosen path could escape anywhere on disk.
So the whole feature is built around **one sandboxed root** and **one path guard**
that every tool funnels through.

After the Layer-1 foundation (registry + `@tool` + plugin loader) and the routing
unification (the registry is the single source of truth), adding a capability is
"register one or more `@tool`s, optionally add a keyword fast-path." File-system
adds enough non-trivial logic (a workspace resolver + a traversal guard) that it
earns its **own module** rather than bloating `builtins.py`.

## Goals

- Four registry tools — `list_files`, `read_file`, `write_file`, `search_files` —
  each **returning** a spoken-friendly string (no `speak`), in a new
  `core/agent/fs_tools.py`.
- **One sandbox root**: `user_data_dir() / "workspace"`. Every path argument is
  resolved through a single `_resolve_in_workspace()` guard that rejects absolute
  paths, drive letters, and `../` traversal. No tool can touch anything outside.
- `write_file` **refuses to overwrite** an existing file (no voice command can
  destroy saved content).
- `list_files` reachable via the **instant keyword fast-path**; all four reachable
  via the LLM agent (automatic once registered).
- **Lean / free / local:** stdlib `pathlib` only — no new dependency.
- All tests **CI-safe** (monkeypatch the workspace resolver to a `tmp_path`; never
  touch real `%APPDATA%`).

## Non-goals

- No delete/move/rename, no subdirectory creation, no append mode, no content
  (full-text) search, no binary/image files, no file-watching, no configurable
  root (the workspace is fixed under `user_data_dir()`).
- No `write_file` keyword fast-path (the filename + content are arbitrary and
  cannot be deterministically extracted by substring rules).
- Not a release; no version bump (Release Drafter accumulates it under v3.4).

---

## Design

### Sandbox & path guard

The single root is `user_data_dir() / "workspace"`:

- **Dev (source):** `<repo>/workspace`
- **Frozen:** `%APPDATA%\JarvisAI\workspace`

It is created lazily (`mkdir(parents=True, exist_ok=True)`) on first use, never at
import time. A module-level resolver returns it so tests can monkeypatch one seam:

```python
def _workspace():

    root = user_data_dir() / "workspace"

    root.mkdir(parents=True, exist_ok=True)

    return root
```

Every path argument from voice/LLM goes through one guard:

```python
def _resolve_in_workspace(name):
    """Resolve a user-supplied name inside the workspace, or None if it escapes.

    Rejects absolute paths / drive letters and any path whose resolved real
    location is not inside the workspace root (blocks ../ traversal). Returns
    the safe absolute Path, or None.
    """

    if not name or not name.strip():

        return None

    candidate = Path(name.strip())

    if candidate.is_absolute() or candidate.drive:

        return None

    root = _workspace()

    resolved = (root / candidate).resolve()

    if resolved == root or root not in resolved.parents:

        return None

    return resolved
```

`Path.resolve()` collapses `..` segments, so `_resolve_in_workspace("../secrets")`
resolves outside `root` and `root not in resolved.parents` is `True` → `None`.
A `None` from any tool returns the spoken refusal `"That path is outside my
workspace."` and touches nothing. This guard is the security core of "sandboxed
root" — the one place to audit.

### New `@tool`s in `core/agent/fs_tools.py`

Module top: `from pathlib import Path`, `from core.paths import user_data_dir`,
`from core.agent.registry import tool`, `from core.utils.logger import logger`, and
a `FILE_PREVIEW_LIMIT = 200` constant (mirrors the clipboard preview cap) and a
`FILE_LIST_LIMIT = 20` constant (caps how many names `list_files`/`search_files`
read aloud). A shared `_preview(text)` helper produces the verbatim-or-truncated
spoken form (its length report reads `"Your file has N characters…"`).

**`list_files()`** — no params:

```python
@tool("list_files", "List the files in your Jarvis workspace folder")
def list_files():

    names = sorted(p.name for p in _workspace().iterdir() if p.is_file())

    if not names:

        return "Your workspace is empty."

    if len(names) <= FILE_LIST_LIMIT:

        return "Your workspace has: " + ", ".join(names) + "."

    shown = ", ".join(names[:FILE_LIST_LIMIT])

    return f"Your workspace has {len(names)} files, including: {shown}."
```

**`read_file(name)`** — required `str` `name`:

```python
@tool(
    "read_file",
    "Read a text file from your Jarvis workspace folder",
    params={"name": {"type": "str", "required": True,
                     "desc": "the file to read, e.g. notes.txt"}},
)
def read_file(name):

    path = _resolve_in_workspace(name)

    if path is None:

        return "That path is outside my workspace."

    if not path.is_file():

        return f"I couldn't find {name} in your workspace."

    try:

        text = path.read_text(encoding="utf-8")

    except (OSError, UnicodeDecodeError) as e:

        logger.warning(f"read_file failed for {name!r}: {e}")

        return f"I couldn't read {name}."

    if not text.strip():

        return f"{name} is empty."

    return _preview(text)
```

`_preview` returns the text verbatim when `<= 200` chars, else a length report +
200-char truncated preview — identical to `read_clipboard`'s philosophy (caps
spoken output, no huge blob read aloud).

**`write_file(name, content)`** — required `str` `name` and `content`:

```python
@tool(
    "write_file",
    "Save text to a new file in your Jarvis workspace folder",
    params={
        "name": {"type": "str", "required": True,
                 "desc": "the file name to save, e.g. notes.txt"},
        "content": {"type": "str", "required": True,
                    "desc": "the text to write into the file"},
    },
)
def write_file(name, content):

    path = _resolve_in_workspace(name)

    if path is None:

        return "That path is outside my workspace."

    if path.exists():

        return f"{name} already exists; pick another name."

    try:

        path.write_text(content, encoding="utf-8")

    except OSError as e:

        logger.warning(f"write_file failed for {name!r}: {e}")

        return f"I couldn't save {name}."

    return f"Saved {name}."
```

**Refuse-on-exist** is enforced *after* the path guard, so a misheard filename can
never replace saved content.

**`search_files(query)`** — required `str` `query`:

```python
@tool(
    "search_files",
    "Find files in your Jarvis workspace whose name matches a query",
    params={"query": {"type": "str", "required": True,
                      "desc": "text to match against file names"}},
)
def search_files(query):

    q = query.strip().lower()

    matches = sorted(
        p.name for p in _workspace().iterdir()
        if p.is_file() and q in p.name.lower()
    )

    if not matches:

        return f"No files match {query}."

    if len(matches) <= FILE_LIST_LIMIT:

        return "Matches: " + ", ".join(matches) + "."

    shown = ", ".join(matches[:FILE_LIST_LIMIT])

    return f"{len(matches)} files match, including: {shown}."
```

Name-only, case-insensitive substring match. Content search is a non-goal for v1
(reading every file on a voice command is slow and unbounded).

### Loader change (`core/agent/loader.py`)

`load_builtins()` currently only imports `core.agent.builtins`. Extend it to also
load the new module with the same re-import dance (pop from `sys.modules` so
re-import re-runs the `@tool` decorators — important for tests that reload):

```python
def load_builtins():

    import sys

    for mod in ("core.agent.builtins", "core.agent.fs_tools"):

        sys.modules.pop(mod, None)

    import core.agent.builtins   # noqa: F401  (decorators register on import)

    import core.agent.fs_tools   # noqa: F401
```

### Routing — keyword fast-path (`core/router/intent_router.py`)

Only `list_files` is zero-arg, so only it gets a fast-path. Add a phrase tuple and
an entry to the existing `_SUBSTRING_TOOLS` table:

```python
_LIST_FILES = (
    "list files",
    "list my files",
    "what files do i have",
    "what's in my workspace",
    "show my files",
    "show my workspace",
)
```

```python
    (_LIST_FILES, ToolCall("list_files", {})),
```

`read_file` / `write_file` / `search_files` need an argument extracted from the
phrase → **LLM-only** (the tool agent fills args). `decide_tool`'s registry-name
word-gate passes utterances containing "file"/"read"/"write"/"search" through to
the LLM, which maps them and fills the args. No brittle keyword arg-extraction.

### Behavior summary

| Utterance | Path | Result |
|---|---|---|
| `"list my files"` | keyword (instant) | `list_files` |
| `"what's in my workspace"` | keyword (instant) | `list_files` |
| `"read notes.txt"` | LLM agent | `read_file{name:"notes.txt"}` |
| `"save a file called todo.txt with buy milk"` | LLM agent | `write_file{name:"todo.txt", content:"buy milk"}` |
| `"search my files for report"` | LLM agent | `search_files{query:"report"}` |
| read a missing file | — | `"I couldn't find <name> in your workspace."` |
| write over an existing file | — | `"<name> already exists; pick another name."` |
| any `../` / absolute / drive path | — | `"That path is outside my workspace."` |
| read a 3000-char file | — | length + 200-char truncated preview |

### Error handling

Every tool returns a spoken string and never raises (the executor already wraps
handlers, but tools degrade gracefully on their own): path escape → refusal;
missing file → friendly "couldn't find"; `OSError`/`UnicodeDecodeError` on
read/write → "I couldn't read/save that file." + `logger.warning`. A binary or
non-UTF-8 file is reported as unreadable, not a crash.

---

## Testing (all CI-safe — monkeypatched workspace, no real %APPDATA%)

**`tests/test_fs_tools.py`** (monkeypatch `fs_tools._workspace` to return a
pytest `tmp_path`):

- **path guard:** `_resolve_in_workspace("../secrets")`, `"/etc/passwd"`,
  `"C:\\Windows\\x"`, `""`, `"   "` → all `None`; `"notes.txt"` → a Path inside the
  temp root.
- **write then refuse:** `write_file("a.txt", "hi")` → `"Saved a.txt."` and the
  file exists with the content; a second `write_file("a.txt", "bye")` →
  `"a.txt already exists; pick another name."` and content is still `"hi"`.
- **write escape:** `write_file("../evil.txt", "x")` → refusal; no file created
  outside the root.
- **read:** missing → "couldn't find"; empty file → "is empty"; short → verbatim;
  3000-char → starts `"Your file has"`/length report + ends `"(truncated)."` and
  `len(out) < 300`.
- **read escape:** `read_file("../../x")` → refusal.
- **search:** populate temp root → hit returns matching names; miss → `"No files
  match <query>."`; case-insensitive.
- **list:** empty root → `"Your workspace is empty."`; populated → names listed.
- **registration:** after `loader.load_builtins()`, all four tools are in the
  registry.

**`tests/test_intent_router.py`** additions:

- Each phrase in `_LIST_FILES` → `ToolCall("list_files", {})` (parametrized).
- substring-in-sentence: `"hey jarvis list my files please"` →
  `ToolCall("list_files", {})`.
- `"read notes.txt"` → `None` (correctly falls through to the LLM path).

## Risks / mitigations

- **Path traversal (the core risk):** one guard, `Path.resolve()` +
  `root not in resolved.parents`, rejects absolute/drive/`..`. Tested with several
  escape vectors. Every tool funnels through it.
- **Voice-mangled filenames overwriting data:** `write_file` refuses on existing
  paths — no command can destroy saved content.
- **Spoken-output blowup:** `read_file` reuses the 200-char preview cap; `list`/
  `search` cap the number of names listed (`FILE_LIST_LIMIT`).
- **Binary/non-UTF-8 files:** `read_text(encoding="utf-8")` may raise
  `UnicodeDecodeError`; caught and reported as unreadable.
- **`list_files` keyword greediness:** phrases are multi-word and workspace/file
  specific, so they won't collide with `open`/`close`/volume triggers.

## Out of scope

- Delete/move/rename, subdirectory creation, append mode, full-text content
  search, binary/image handling, file-watching, a configurable root, a
  `write_file` keyword fast-path.
