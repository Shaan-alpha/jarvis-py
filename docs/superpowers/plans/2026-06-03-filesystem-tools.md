# File-system Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four sandboxed file-system tools (`list_files`, `read_file`, `write_file`, `search_files`) to the Jarvis tool agent, confined to a single workspace folder.

**Architecture:** A new `core/agent/fs_tools.py` module holds the four `@tool`-decorated functions plus a workspace resolver and one path-traversal guard every tool funnels through. The loader imports the module so the decorators register; `list_files` (zero-arg) gets a keyword fast-path in the router, the rest are LLM-only.

**Tech Stack:** Python stdlib `pathlib` only (no new dependency); existing `@tool` registry; pytest with `tmp_path` + monkeypatch for CI-safe tests.

**Spec:** [docs/superpowers/specs/2026-06-03-filesystem-tools-design.md](../specs/2026-06-03-filesystem-tools-design.md)

---

### Task 1: Module scaffold — workspace resolver + path guard + helpers

This is the security core. The guard is what makes the sandbox real, so it is built and tested first.

**Files:**
- Create: `core/agent/fs_tools.py`
- Test: `tests/test_fs_tools.py`

- [ ] **Step 1: Write the failing tests for the path guard**

Create `tests/test_fs_tools.py`:

```python
from core.agent import fs_tools


def _patch_workspace(monkeypatch, tmp_path):
    monkeypatch.setattr(fs_tools, "_workspace", lambda: tmp_path)


def test_resolve_rejects_parent_traversal(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools._resolve_in_workspace("../secrets") is None


def test_resolve_rejects_absolute_path(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools._resolve_in_workspace("/etc/passwd") is None


def test_resolve_rejects_drive_path(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools._resolve_in_workspace(r"C:\Windows\system32") is None


def test_resolve_rejects_empty(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools._resolve_in_workspace("") is None
    assert fs_tools._resolve_in_workspace("   ") is None


def test_resolve_rejects_workspace_root_itself(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools._resolve_in_workspace(".") is None


def test_resolve_accepts_simple_name(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    resolved = fs_tools._resolve_in_workspace("notes.txt")
    assert resolved == (tmp_path / "notes.txt").resolve()


def test_preview_short_returns_verbatim():
    assert fs_tools._preview("hello") == "hello"


def test_preview_long_is_truncated():
    out = fs_tools._preview("x" * 3000)
    assert out.startswith("Your file has")
    assert "3000 characters" in out
    assert out.endswith("(truncated).")
    assert len(out) < 300
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_fs_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.agent.fs_tools'`

- [ ] **Step 3: Create the module with the resolver, guard, and preview helper**

Create `core/agent/fs_tools.py` (match `builtins.py` style — a blank line between most statements, grouped imports):

```python
from pathlib import Path

from core.paths import user_data_dir

from core.agent.registry import tool

from core.utils.logger import logger


FILE_PREVIEW_LIMIT = 200

FILE_LIST_LIMIT = 20


def _workspace():

    root = user_data_dir() / "workspace"

    root.mkdir(parents=True, exist_ok=True)

    return root


def _resolve_in_workspace(name):
    """Resolve a user-supplied name inside the workspace, or None if it escapes.

    Rejects empty input, absolute paths / drive letters, and any path whose
    resolved real location is not strictly inside the workspace root (blocks
    ../ traversal and the root itself). Returns the safe absolute Path, or None.
    """

    if not name or not name.strip():

        return None

    candidate = Path(name.strip())

    if candidate.is_absolute() or candidate.drive:

        return None

    root = _workspace().resolve()

    resolved = (root / candidate).resolve()

    if resolved == root or root not in resolved.parents:

        return None

    return resolved


def _preview(text):
    """Verbatim if short; otherwise a length report + truncated preview.

    Mirrors read_clipboard so spoken output never reads a huge blob aloud.
    """

    if len(text) <= FILE_PREVIEW_LIMIT:

        return text

    return (
        f"Your file has {len(text)} characters. "
        f'It starts: "{text[:FILE_PREVIEW_LIMIT]}..." (truncated).'
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_fs_tools.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add core/agent/fs_tools.py tests/test_fs_tools.py
git commit -m "feat(fs): workspace resolver + path-traversal guard

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `list_files` tool

**Files:**
- Modify: `core/agent/fs_tools.py` (append the tool)
- Test: `tests/test_fs_tools.py` (append cases)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_fs_tools.py`:

```python
def test_list_files_empty(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools.list_files() == "Your workspace is empty."


def test_list_files_lists_names(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.txt").write_text("y")
    out = fs_tools.list_files()
    assert "a.txt" in out
    assert "b.txt" in out


def test_list_files_ignores_directories(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("x")
    out = fs_tools.list_files()
    assert "a.txt" in out
    assert "sub" not in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_fs_tools.py -k list_files -v`
Expected: FAIL with `AttributeError: module 'core.agent.fs_tools' has no attribute 'list_files'`

- [ ] **Step 3: Append the tool to `core/agent/fs_tools.py`**

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

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_fs_tools.py -k list_files -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add core/agent/fs_tools.py tests/test_fs_tools.py
git commit -m "feat(fs): list_files tool

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `read_file` tool

**Files:**
- Modify: `core/agent/fs_tools.py` (append the tool)
- Test: `tests/test_fs_tools.py` (append cases)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_fs_tools.py`:

```python
def test_read_file_missing(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools.read_file("nope.txt") == \
        "I couldn't find nope.txt in your workspace."


def test_read_file_empty(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "e.txt").write_text("")
    assert fs_tools.read_file("e.txt") == "e.txt is empty."


def test_read_file_short_returns_verbatim(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "s.txt").write_text("hello world")
    assert fs_tools.read_file("s.txt") == "hello world"


def test_read_file_long_is_truncated(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "big.txt").write_text("x" * 3000)
    out = fs_tools.read_file("big.txt")
    assert out.startswith("Your file has")
    assert len(out) < 300


def test_read_file_rejects_traversal(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    assert fs_tools.read_file("../../etc/passwd") == \
        "That path is outside my workspace."
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_fs_tools.py -k read_file -v`
Expected: FAIL with `AttributeError: module 'core.agent.fs_tools' has no attribute 'read_file'`

- [ ] **Step 3: Append the tool to `core/agent/fs_tools.py`**

```python
@tool(
    "read_file",
    "Read a text file from your Jarvis workspace folder",
    params={
        "name": {
            "type": "str",
            "required": True,
            "desc": "the file to read, e.g. notes.txt",
        }
    },
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_fs_tools.py -k read_file -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add core/agent/fs_tools.py tests/test_fs_tools.py
git commit -m "feat(fs): read_file tool with preview truncation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `write_file` tool (refuse-on-exist)

**Files:**
- Modify: `core/agent/fs_tools.py` (append the tool)
- Test: `tests/test_fs_tools.py` (append cases)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_fs_tools.py`:

```python
def test_write_file_creates_and_confirms(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    out = fs_tools.write_file("a.txt", "hi")
    assert out == "Saved a.txt."
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hi"


def test_write_file_refuses_overwrite(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "a.txt").write_text("original")
    out = fs_tools.write_file("a.txt", "replacement")
    assert out == "a.txt already exists; pick another name."
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "original"


def test_write_file_rejects_traversal(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    out = fs_tools.write_file("../evil.txt", "x")
    assert out == "That path is outside my workspace."
    assert not (tmp_path.parent / "evil.txt").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_fs_tools.py -k write_file -v`
Expected: FAIL with `AttributeError: module 'core.agent.fs_tools' has no attribute 'write_file'`

- [ ] **Step 3: Append the tool to `core/agent/fs_tools.py`**

```python
@tool(
    "write_file",
    "Save text to a new file in your Jarvis workspace folder",
    params={
        "name": {
            "type": "str",
            "required": True,
            "desc": "the file name to save, e.g. notes.txt",
        },
        "content": {
            "type": "str",
            "required": True,
            "desc": "the text to write into the file",
        },
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_fs_tools.py -k write_file -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add core/agent/fs_tools.py tests/test_fs_tools.py
git commit -m "feat(fs): write_file tool (refuse-on-exist)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `search_files` tool

**Files:**
- Modify: `core/agent/fs_tools.py` (append the tool)
- Test: `tests/test_fs_tools.py` (append cases)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_fs_tools.py`:

```python
def test_search_files_hit(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "report-q1.txt").write_text("x")
    (tmp_path / "notes.txt").write_text("y")
    out = fs_tools.search_files("report")
    assert "report-q1.txt" in out
    assert "notes.txt" not in out


def test_search_files_case_insensitive(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "Report.txt").write_text("x")
    out = fs_tools.search_files("report")
    assert "Report.txt" in out


def test_search_files_miss(monkeypatch, tmp_path):
    _patch_workspace(monkeypatch, tmp_path)
    (tmp_path / "notes.txt").write_text("y")
    assert fs_tools.search_files("invoice") == "No files match invoice."
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_fs_tools.py -k search_files -v`
Expected: FAIL with `AttributeError: module 'core.agent.fs_tools' has no attribute 'search_files'`

- [ ] **Step 3: Append the tool to `core/agent/fs_tools.py`**

```python
@tool(
    "search_files",
    "Find files in your Jarvis workspace whose name matches a query",
    params={
        "query": {
            "type": "str",
            "required": True,
            "desc": "text to match against file names",
        }
    },
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_fs_tools.py -k search_files -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add core/agent/fs_tools.py tests/test_fs_tools.py
git commit -m "feat(fs): search_files tool (name match)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Loader registration

The tools only register when their module is imported. `load_builtins()` currently imports only `core.agent.builtins`; extend it to import `core.agent.fs_tools` too, with the same `sys.modules.pop` re-import dance.

**Files:**
- Modify: `core/agent/loader.py:36-43` (the `load_builtins` function)
- Test: `tests/test_fs_tools.py` (append a registration case)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_fs_tools.py`:

```python
def test_fs_tools_registered():
    from core.agent import loader, registry
    loader.load_builtins()
    for name in ("list_files", "read_file", "write_file", "search_files"):
        assert registry.get(name) is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fs_tools.py::test_fs_tools_registered -v`
Expected: FAIL — `assert registry.get('list_files') is not None` fails (loader does not import fs_tools yet)

- [ ] **Step 3: Update `load_builtins` in `core/agent/loader.py`**

Replace the existing `load_builtins` function:

```python
def load_builtins():

    import sys

    # Remove from sys.modules so re-import always re-executes @tool decorators.
    for mod in ("core.agent.builtins", "core.agent.fs_tools"):

        sys.modules.pop(mod, None)

    import core.agent.builtins   # noqa: F401  (decorators register on import)

    import core.agent.fs_tools   # noqa: F401  (decorators register on import)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fs_tools.py::test_fs_tools_registered -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/agent/loader.py tests/test_fs_tools.py
git commit -m "feat(fs): register file-system tools via loader

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: `list_files` keyword fast-path

`list_files` is zero-arg, so it gets an instant router fast-path. The arg-bearing tools (`read_file`/`write_file`/`search_files`) stay LLM-only.

**Files:**
- Modify: `core/router/intent_router.py` (add `_LIST_FILES` tuple + a `_SUBSTRING_TOOLS` entry)
- Test: `tests/test_intent_router.py` (append cases)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_intent_router.py`:

```python
import pytest

from core.router.intent_router import resolve_keyword_tool


_LIST_FILES_PHRASES = [
    "list files",
    "list my files",
    "what files do i have",
    "what's in my workspace",
    "show my files",
    "show my workspace",
]


@pytest.mark.parametrize("phrase", _LIST_FILES_PHRASES)
def test_list_files_keyword_path(phrase):
    call = resolve_keyword_tool(phrase)
    assert call is not None
    assert call.name == "list_files"
    assert call.args == {}


def test_list_files_substring_in_sentence():
    call = resolve_keyword_tool("hey jarvis list my files please")
    assert call is not None
    assert call.name == "list_files"


def test_read_file_falls_through_to_llm():
    # Arg-bearing fs tools are LLM-only; the keyword resolver must miss.
    assert resolve_keyword_tool("read notes.txt") is None
```

(If `test_intent_router.py` already imports `pytest` or `resolve_keyword_tool` at the top, do not duplicate the imports — append only the new constant and test functions.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_intent_router.py -k "list_files or read_file_falls" -v`
Expected: FAIL — `resolve_keyword_tool("list files")` returns `None` (no `list_files` branch yet)

- [ ] **Step 3: Add the fast-path in `core/router/intent_router.py`**

After the `_CLIPBOARD_READ` tuple (before `_SEARCH_TRIGGERS`), add:

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

Then add an entry to the `_SUBSTRING_TOOLS` tuple (after the `_CLIPBOARD_READ` row):

```python
    (_LIST_FILES, ToolCall("list_files", {})),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_intent_router.py -k "list_files or read_file_falls" -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add core/router/intent_router.py tests/test_intent_router.py
git commit -m "feat(fs): list_files keyword fast-path

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Full suite + lint verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest`
Expected: PASS — all prior tests plus the ~25 new fs/router tests green.

- [ ] **Step 2: Run build-breaking lint (must be 0)**

Run: `python -m flake8 . --select=E9,F63,F7,F82,F401 --exclude=venv,__pycache__,dist,build --count`
Expected: `0`

- [ ] **Step 3: Run quality lint (warnings only)**

Run: `python -m flake8 . --exit-zero --max-complexity=10 --max-line-length=127 --exclude=venv,__pycache__,dist,build`
Expected: no new complexity/line-length warnings from `fs_tools.py` or the edits.

- [ ] **Step 4: Update `.gitignore` so the runtime workspace is never committed**

Add to `.gitignore` (the workspace folder holds user files at runtime in dev):

```
workspace/
```

- [ ] **Step 5: Commit the gitignore change**

```bash
git add .gitignore
git commit -m "chore(fs): gitignore the runtime workspace folder

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
