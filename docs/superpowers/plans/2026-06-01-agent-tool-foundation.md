# Agent Tool Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace jarvis-py's flat, parameterless tool-agent with a parameterized tool protocol, a decorator-based registry, and a drop-in plugin loader — proven by one parameterized built-in (`open_app`) and one example plugin (`roll_dice`).

**Architecture:** Tools register as `ToolSpec`s (name + description + typed `ParamSpec` args + handler callable) via a `@tool(...)` decorator into a process-wide registry. The LLM selector (`decide_tool`) builds its prompt from the registry, returns a validated `ToolCall | None`; the executor (`execute_tool`) is a generic registry lookup + dispatch. A loader imports built-ins and any `plugins/*.py` so their decorators self-register. Everything degrades to normal chat on any error.

**Tech Stack:** Python 3.10+, stdlib only for the new code (`dataclasses`, `importlib`, `json`, `re`), `requests` (already used) for Ollama, `pytest` + `monkeypatch` for tests. No new dependency.

**Branch:** `feature/v3.4-agent-foundation` (already created; the spec commit `08879dd` is its first commit).

**Spec:** [`docs/superpowers/specs/2026-06-01-agent-tool-foundation-design.md`](../specs/2026-06-01-agent-tool-foundation-design.md)

**House style:** `core/**` files use the "blank line between most statements" idiom (mirror [`core/agent/tool_agent.py`](../../../core/agent/tool_agent.py)). Test files use the tighter style of [`tests/test_process_query.py`](../../../tests/test_process_query.py). Line length ≤ 127; complexity ≤ 10.

**Run tests:** `python -m pytest` · **Run one:** `python -m pytest tests/test_x.py::test_y -v`
**Build-breaking lint (must be 0):** `python -m flake8 . --select=E9,F63,F7,F82,F401 --exclude=venv,__pycache__,dist,build --count`

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `core/agent/registry.py` | `@tool` decorator, `ParamSpec`/`ToolSpec`/`ToolCall`, the global registry, `coerce_and_validate`. | 1, 2 |
| `tests/conftest.py` | Autouse fixture: snapshot/restore the registry around every test (deterministic isolation). | 1 |
| `tests/test_registry.py` | Registry + validation unit tests. | 1, 2 |
| `core/agent/builtins.py` | The 6 existing tools as decorated functions + `open_app` + pure `resolve_app`. | 3 |
| `tests/test_open_app.py` | `resolve_app` + `open_app` + builtins-presence tests. | 3 |
| `core/agent/loader.py` | `init_tools()`, `load_builtins()`, `load_plugins(dirs)`, `_import_file`, `_plugin_dirs`. | 4 |
| `tests/test_loader.py` | Plugin discovery / isolation / dedupe tests. | 4 |
| `core/agent/tool_agent.py` | `decide_tool(query) -> ToolCall \| None`: registry-aware gate, registry-built prompt, balanced-JSON parse, validate. | 5 |
| `tests/test_tool_agent.py` | Gate + selector + arg-validation tests (Ollama mocked). | 5 |
| `core/agent/tool_executor.py` | `execute_tool(call) -> str \| None`: registry lookup + dispatch. | 6 |
| `tests/test_tool_executor.py` | Dispatch / unknown / handler-error tests. | 6 |
| `app.py` | Import + call `init_tools()`; `"none"` sentinel → `None` in `process_query`. | 7 |
| `tests/test_process_query.py` | Regression: `decide_tool` patched to return `None`. | 7 |
| `plugins/roll_dice.py` + `plugins/README.md` | Example drop-in plugin + the contract docs. | 8 |
| `core/agent/tool_registry.py` | **Deleted** (superseded by `registry.py`). | 9 |
| `jarvis.spec` | Add `("plugins", "plugins")` to `datas` for the frozen build. | 9 |

---

## Task 1: Registry data model + registration API + test isolation

**Files:**
- Create: `core/agent/registry.py`
- Create: `tests/conftest.py`
- Test: `tests/test_registry.py`

- [ ] **Step 1: Write `tests/conftest.py`** (deterministic registry isolation — the registry is a module global, so without this a `clear()` in one test would leak into others)

```python
import pytest

from core.agent import registry
from core.agent import loader


@pytest.fixture(autouse=True)
def _isolate_registry():
    # Make sure built-ins are imported once, then snapshot the registry and
    # restore it after each test so a clear()/register inside a test never
    # leaks into another.
    loader.load_builtins()
    snapshot = dict(registry._REGISTRY)
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(snapshot)
```

- [ ] **Step 2: Write the failing test** `tests/test_registry.py`

```python
from core.agent import registry


def test_tool_decorator_registers():
    registry.clear()

    @registry.tool("ping", "say pong")
    def _ping():
        return "pong"

    spec = registry.get("ping")
    assert spec is not None
    assert spec.name == "ping"
    assert spec.description == "say pong"
    assert spec.params == {}
    assert spec.handler() == "pong"


def test_tool_decorator_builds_param_specs():
    registry.clear()

    @registry.tool("greet", "greet someone",
                   params={"who": {"type": "str", "required": True, "desc": "name"}})
    def _greet(who):
        return f"hi {who}"

    spec = registry.get("greet")
    assert set(spec.params) == {"who"}
    assert spec.params["who"].type == "str"
    assert spec.params["who"].required is True
    assert spec.params["who"].desc == "name"


def test_all_tools_and_clear():
    registry.clear()

    @registry.tool("a", "tool a")
    def _a():
        return None

    @registry.tool("b", "tool b")
    def _b():
        return None

    assert {s.name for s in registry.all_tools()} == {"a", "b"}
    registry.clear()
    assert registry.all_tools() == []


def test_duplicate_name_last_wins():
    registry.clear()

    @registry.tool("dup", "first")
    def _first():
        return "first"

    @registry.tool("dup", "second")
    def _second():
        return "second"

    assert registry.get("dup").handler() == "second"
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `python -m pytest tests/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.agent.registry'` (and conftest import error is fine to see here).

- [ ] **Step 4: Implement `core/agent/registry.py`** (registration half — `coerce_and_validate` comes in Task 2)

```python
from dataclasses import dataclass

from typing import Callable

from core.utils.logger import (
    logger
)


@dataclass(frozen=True)
class ParamSpec:

    type: str = "str"

    required: bool = True

    desc: str = ""

    default: object = None


@dataclass(frozen=True)
class ToolSpec:

    name: str

    description: str

    params: dict          # name -> ParamSpec

    handler: Callable


@dataclass(frozen=True)
class ToolCall:

    name: str

    args: dict


_REGISTRY = {}


def register(spec):

    if spec.name in _REGISTRY:

        logger.warning(f"Tool {spec.name!r} re-registered; overwriting")

    _REGISTRY[spec.name] = spec


def get(name):

    return _REGISTRY.get(name)


def all_tools():

    return list(_REGISTRY.values())


def clear():

    _REGISTRY.clear()


def tool(name, description, params=None):

    param_specs = {}

    for pname, pmeta in (params or {}).items():

        param_specs[pname] = ParamSpec(
            type=pmeta.get("type", "str"),
            required=pmeta.get("required", True),
            desc=pmeta.get("desc", ""),
            default=pmeta.get("default", None),
        )

    def decorator(func):

        register(
            ToolSpec(
                name=name,
                description=description,
                params=param_specs,
                handler=func,
            )
        )

        return func

    return decorator
```

> Note: `conftest.py` imports `core.agent.loader`, which doesn't exist until Task 4. Until then, run `tests/test_registry.py` with a temporary minimal conftest OR create the loader stub first. **Simplest: do Step 5 (temporary conftest shim) below**, then replace it in Task 4.

- [ ] **Step 5: Temporary conftest shim** so Task 1–3 can run before the loader exists. Replace the `loader.load_builtins()` line in `tests/conftest.py` with a guarded import for now:

```python
import pytest

from core.agent import registry

try:
    from core.agent import loader
except ImportError:
    loader = None


@pytest.fixture(autouse=True)
def _isolate_registry():
    if loader is not None:
        loader.load_builtins()
    snapshot = dict(registry._REGISTRY)
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(snapshot)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_registry.py -v`
Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add core/agent/registry.py tests/conftest.py tests/test_registry.py
git commit -m "feat(agent): tool registry + @tool decorator + test isolation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Argument coercion + validation

**Files:**
- Modify: `core/agent/registry.py` (add `coerce_and_validate`)
- Test: `tests/test_registry.py` (add tests)

- [ ] **Step 1: Write the failing tests** (append to `tests/test_registry.py`)

```python
from core.agent.registry import ParamSpec, ToolSpec, coerce_and_validate


def _spec(params):
    return ToolSpec("t", "d", params, lambda **k: None)


def test_coerce_int_and_str():
    spec = _spec({"n": ParamSpec(type="int"), "s": ParamSpec(type="str")})
    args, err = coerce_and_validate(spec, {"n": "5", "s": 7})
    assert err is None
    assert args == {"n": 5, "s": "7"}


def test_default_filled_for_missing_optional():
    spec = _spec({"sides": ParamSpec(type="int", required=False, default=6)})
    args, err = coerce_and_validate(spec, {})
    assert err is None
    assert args == {"sides": 6}


def test_missing_required_is_error():
    spec = _spec({"name": ParamSpec(type="str", required=True)})
    args, err = coerce_and_validate(spec, {})
    assert err is not None
    assert "name" in err


def test_uncoercible_is_error():
    spec = _spec({"n": ParamSpec(type="int", required=True)})
    args, err = coerce_and_validate(spec, {"n": "not-a-number"})
    assert err is not None


def test_unknown_keys_dropped():
    spec = _spec({"n": ParamSpec(type="int", required=False, default=0)})
    args, err = coerce_and_validate(spec, {"n": 1, "bogus": "x"})
    assert err is None
    assert args == {"n": 1}
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_registry.py -k coerce -v`
Expected: FAIL — `ImportError: cannot import name 'coerce_and_validate'`.

- [ ] **Step 3: Implement `coerce_and_validate`** (append to `core/agent/registry.py`)

```python
_COERCERS = {
    "str": str,
    "int": int,
}


def coerce_and_validate(spec, raw_args):

    raw_args = raw_args or {}

    result = {}

    for pname, pspec in spec.params.items():

        if pname in raw_args and raw_args[pname] is not None:

            coercer = _COERCERS.get(pspec.type, str)

            try:

                result[pname] = coercer(raw_args[pname])

            except (TypeError, ValueError):

                return {}, f"param {pname!r} not coercible to {pspec.type}"

        elif pspec.required:

            return {}, f"missing required param {pname!r}"

        else:

            result[pname] = pspec.default

    return result, None
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_registry.py -v`
Expected: PASS (9 tests total).

- [ ] **Step 5: Commit**

```bash
git add core/agent/registry.py tests/test_registry.py
git commit -m "feat(agent): stdlib arg coercion + validation for tool params

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Built-in tools + `open_app` resolver

**Files:**
- Create: `core/agent/builtins.py`
- Test: `tests/test_open_app.py`

- [ ] **Step 1: Write the failing tests** `tests/test_open_app.py`

```python
from core.agent import builtins as agent_builtins
from core.agent import registry


def test_resolve_app_alias():
    assert agent_builtins.resolve_app("Calculator") == "calc"


def test_resolve_app_passthrough():
    assert agent_builtins.resolve_app("notepad") == "notepad"


def test_open_app_calls_startfile(monkeypatch):
    calls = []
    monkeypatch.setattr(agent_builtins.os, "startfile",
                        lambda target: calls.append(target), raising=False)
    out = agent_builtins.open_app("calculator")
    assert calls == ["calc"]
    assert out == "Opening calculator."


def test_builtins_registered():
    from core.agent import loader
    loader.load_builtins()
    for name in ("open_app", "open_calculator", "open_youtube", "open_google",
                 "increase_volume", "decrease_volume", "mute_volume"):
        assert registry.get(name) is not None
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_open_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.agent.builtins'`.

- [ ] **Step 3: Implement `core/agent/builtins.py`**

```python
import os

import webbrowser

from core.agent.registry import (
    tool
)


_APP_ALIASES = {
    "calculator": "calc",
    "calc": "calc",
    "notepad": "notepad",
    "paint": "mspaint",
    "explorer": "explorer",
    "files": "explorer",
    "cmd": "cmd",
    "command prompt": "cmd",
    "terminal": "cmd",
    "spotify": "spotify:",
    "chrome": "chrome",
    "edge": "msedge",
    "browser": "msedge",
}


def resolve_app(name):

    key = name.strip().lower()

    return _APP_ALIASES.get(key, key)


@tool(
    "open_app",
    "Open a Windows application by name (e.g. notepad, calculator, spotify)",
    params={
        "name": {
            "type": "str",
            "required": True,
            "desc": "the app to open, e.g. notepad",
        }
    },
)
def open_app(name):

    target = resolve_app(name)

    try:

        os.startfile(target)

    except OSError:

        import subprocess

        subprocess.Popen(["cmd", "/c", "start", "", target])

    return f"Opening {name}."


@tool("open_calculator", "Open Windows calculator")
def open_calculator():

    os.startfile(r"C:\Windows\System32\calc.exe")

    return "Opening calculator."


@tool("open_youtube", "Open YouTube in the browser")
def open_youtube():

    webbrowser.open("https://youtube.com")

    return "Opening YouTube."


@tool("open_google", "Open Google in the browser")
def open_google():

    webbrowser.open("https://google.com")

    return "Opening Google."


@tool("increase_volume", "Increase system volume")
def increase_volume():

    import pyautogui

    for _ in range(5):

        pyautogui.press("volumeup")

    return "Increasing volume."


@tool("decrease_volume", "Decrease system volume")
def decrease_volume():

    import pyautogui

    for _ in range(5):

        pyautogui.press("volumedown")

    return "Decreasing volume."


@tool("mute_volume", "Mute system volume")
def mute_volume():

    import pyautogui

    pyautogui.press("volumemute")

    return "Volume muted."
```

> `test_builtins_registered` imports `core.agent.loader` (created in Task 4). If you run Task 3 in isolation before Task 4, that one test errors on import — that's expected; it passes once Task 4 lands. The other three tests in this file pass now.

- [ ] **Step 4: Run to verify (3 of 4 pass pre-Task-4)**

Run: `python -m pytest tests/test_open_app.py -v -k "resolve or startfile"`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add core/agent/builtins.py tests/test_open_app.py
git commit -m "feat(agent): builtin tools as decorated functions + open_app resolver

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Plugin loader

**Files:**
- Create: `core/agent/loader.py`
- Test: `tests/test_loader.py`

- [ ] **Step 1: Write the failing tests** `tests/test_loader.py`

```python
from core.agent import loader
from core.agent import registry


def test_load_plugins_registers(tmp_path):
    registry.clear()
    (tmp_path / "myplug.py").write_text(
        "from core.agent.registry import tool\n"
        "@tool('hello', 'say hi')\n"
        "def hello():\n"
        "    return 'hi'\n"
    )
    loader.load_plugins([tmp_path])
    spec = registry.get("hello")
    assert spec is not None
    assert spec.handler() == "hi"


def test_broken_plugin_is_skipped(tmp_path):
    (tmp_path / "bad.py").write_text("raise RuntimeError('boom')\n")
    # Must not raise.
    loader.load_plugins([tmp_path])


def test_missing_dir_is_skipped(tmp_path):
    # Must not raise.
    loader.load_plugins([tmp_path / "does_not_exist"])


def test_underscore_files_ignored(tmp_path):
    registry.clear()
    (tmp_path / "_helper.py").write_text(
        "from core.agent.registry import tool\n"
        "@tool('should_not_load', 'x')\n"
        "def f():\n"
        "    return None\n"
    )
    loader.load_plugins([tmp_path])
    assert registry.get("should_not_load") is None


def test_duplicate_dirs_loaded_once(tmp_path):
    (tmp_path / "p.py").write_text(
        "from core.agent.registry import tool\n"
        "@tool('once', 'x')\n"
        "def f():\n"
        "    return None\n"
    )
    # Passing the same dir twice must not double-import / error.
    loader.load_plugins([tmp_path, tmp_path])
    assert registry.get("once") is not None


def test_init_tools_loads_builtins():
    loader.init_tools()
    assert registry.get("open_app") is not None
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.agent.loader'`.

- [ ] **Step 3: Implement `core/agent/loader.py`**

```python
import importlib.util

from core.paths import (
    resource_dir,
    user_data_dir,
)

from core.utils.logger import (
    logger
)


def _plugin_dirs():

    return [
        resource_dir() / "plugins",
        user_data_dir() / "plugins",
    ]


def _import_file(path):

    spec = importlib.util.spec_from_file_location(path.stem, str(path))

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)


def load_builtins():

    import core.agent.builtins  # noqa: F401  (decorators register on import)


def load_plugins(dirs):

    seen = set()

    for d in dirs:

        resolved = d.resolve()

        if resolved in seen or not d.exists():

            continue

        seen.add(resolved)

        for path in sorted(d.glob("*.py")):

            if path.name.startswith("_"):

                continue

            try:

                _import_file(path)

            except Exception as e:

                logger.exception(f"Skipping bad plugin {path}: {e}")


def init_tools():

    load_builtins()

    load_plugins(_plugin_dirs())
```

- [ ] **Step 4: Replace the temporary conftest shim** with the real version (now that `loader` exists). Edit `tests/conftest.py` back to the Task 1 / Step 1 form (drop the `try/except ImportError`):

```python
import pytest

from core.agent import registry
from core.agent import loader


@pytest.fixture(autouse=True)
def _isolate_registry():
    loader.load_builtins()
    snapshot = dict(registry._REGISTRY)
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(snapshot)
```

- [ ] **Step 5: Run to verify it passes** (loader + the previously-deferred builtins test)

Run: `python -m pytest tests/test_loader.py tests/test_open_app.py -v`
Expected: PASS (6 loader + 4 open_app = 10 tests).

- [ ] **Step 6: Commit**

```bash
git add core/agent/loader.py tests/conftest.py
git commit -m "feat(agent): plugin loader (init_tools/load_builtins/load_plugins)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: `decide_tool` — registry-aware gate + parameterized selector

**Files:**
- Modify: `core/agent/tool_agent.py` (full rewrite of body; keep `ACTION_VERBS`)
- Test: `tests/test_tool_agent.py`

- [ ] **Step 1: Write the failing tests** `tests/test_tool_agent.py`

```python
from core.agent import tool_agent
from core.agent import registry


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _register_open_app():
    @registry.tool("open_app", "Open an app",
                   params={"name": {"type": "str", "required": True}})
    def _open(name):
        return f"Opening {name}."


def test_gate_passes_builtin_verb():
    assert tool_agent._looks_like_action("open notepad") is True


def test_gate_passes_tool_name_token():
    registry.clear()

    @registry.tool("roll_dice", "Roll a die")
    def _r():
        return "rolled"

    assert tool_agent._looks_like_action("roll a dice") is True


def test_gate_blocks_chitchat():
    registry.clear()
    assert tool_agent._looks_like_action("what is python") is False


def test_decide_tool_parameterized(monkeypatch):
    _register_open_app()
    monkeypatch.setattr(
        tool_agent.requests, "post",
        lambda *a, **k: _Resp({"response": '{"tool": "open_app", "args": {"name": "notepad"}}'}),
    )
    call = tool_agent.decide_tool("open notepad")
    assert call == registry.ToolCall("open_app", {"name": "notepad"})


def test_decide_tool_question_is_gated_to_none():
    registry.clear()
    assert tool_agent.decide_tool("what is python") is None


def test_decide_tool_unknown_tool_is_none(monkeypatch):
    registry.clear()
    _register_open_app()
    monkeypatch.setattr(
        tool_agent.requests, "post",
        lambda *a, **k: _Resp({"response": '{"tool": "fly_to_moon", "args": {}}'}),
    )
    assert tool_agent.decide_tool("open notepad") is None


def test_decide_tool_missing_required_arg_is_none(monkeypatch):
    registry.clear()
    _register_open_app()
    monkeypatch.setattr(
        tool_agent.requests, "post",
        lambda *a, **k: _Resp({"response": '{"tool": "open_app", "args": {}}'}),
    )
    assert tool_agent.decide_tool("open something") is None


def test_extract_first_json_handles_nested():
    obj = tool_agent._extract_first_json('noise {"tool": "x", "args": {"a": 1}} trailing')
    assert obj == {"tool": "x", "args": {"a": 1}}
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_tool_agent.py -v`
Expected: FAIL — e.g. `_looks_like_action` no longer registry-aware / `decide_tool` returns a string, not `ToolCall`.

- [ ] **Step 3: Rewrite `core/agent/tool_agent.py`**

```python
import json

import re

import requests

from config.settings import (
    MODEL_NAME,
    OLLAMA_URL
)

from core.agent import (
    registry
)

from core.utils.logger import (
    logger
)


ACTION_VERBS = (
    "open ",
    "launch ",
    "start ",
    "run ",
    "play ",
    "close ",
    "shut ",
    "kill ",
    "stop ",
    "increase ",
    "decrease ",
    "raise ",
    "lower ",
    "turn up ",
    "turn down ",
    "mute ",
    "unmute ",
    "volume ",
)


def _looks_like_action(query):

    q = query.strip().lower()

    if any(q.startswith(v) or f" {v}" in f" {q}" for v in ACTION_VERBS):

        return True

    words = set(re.findall(r"[a-z0-9]+", q))

    for spec in registry.all_tools():

        if words & set(spec.name.lower().split("_")):

            return True

    return False


def _tool_list_text():

    lines = []

    for index, spec in enumerate(registry.all_tools(), start=1):

        if spec.params:

            param_lines = []

            for pname, pspec in spec.params.items():

                req = "required" if pspec.required else "optional"

                param_lines.append(
                    f"     - {pname} ({pspec.type}, {req}): {pspec.desc}"
                )

            params_text = "\n   params:\n" + "\n".join(param_lines)

        else:

            params_text = "\n   params: none"

        lines.append(
            f"{index}. {spec.name}\n   - {spec.description}{params_text}"
        )

    return "\n\n".join(lines)


def _extract_first_json(text):

    text = text.replace("```json", "").replace("```", "")

    start = text.find("{")

    if start == -1:

        return None

    try:

        obj, _ = json.JSONDecoder().raw_decode(text[start:])

        return obj

    except json.JSONDecodeError:

        return None


def decide_tool(query):

    if not _looks_like_action(query):

        return None

    prompt = f"""You are a strict tool selector. Map the user's request to
exactly one of the available tools, OR return "none" if the request is not an
explicit command to perform one of these actions.

Available tools:
{_tool_list_text()}

Strict rules:
- Output ONE JSON object only. No prose, no markdown.
- Shape: {{"tool": "<name>", "args": {{...}}}}  OR  {{"tool": "none"}}.
- Fill "args" using the tool's declared params; take values from the user's words.
- Only choose a tool if the user is explicitly asking to perform it now.
- Questions, explanations, conversation, anything with "what"/"why"/"how"/
  "explain"/"tell me"/"describe" -> {{"tool": "none"}}.
- If unsure, return {{"tool": "none"}}.

Examples:
- "open notepad" -> {{"tool": "open_app", "args": {{"name": "notepad"}}}}
- "increase the volume please" -> {{"tool": "increase_volume", "args": {{}}}}
- "what is python" -> {{"tool": "none"}}

User Request:
{query}

JSON:"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=30
        )

        data = response.json()

        text = data.get("response", "")

        parsed = _extract_first_json(text)

        if parsed is None:

            logger.warning(
                f"Tool agent returned unparseable text: {text[:120]!r}"
            )

            return None

        name = parsed.get("tool", "none")

        if not isinstance(name, str):

            return None

        name = name.strip().lower()

        if name in ("", "none", "null"):

            return None

        spec = registry.get(name)

        if spec is None:

            logger.info(
                f"Tool agent picked unknown tool {name!r}; falling back to chat"
            )

            return None

        raw_args = parsed.get("args", {})

        if not isinstance(raw_args, dict):

            raw_args = {}

        args, error = registry.coerce_and_validate(spec, raw_args)

        if error:

            logger.info(f"Tool {name!r} arg error: {error}; falling back to chat")

            return None

        return registry.ToolCall(name=name, args=args)

    except Exception as e:

        logger.exception(f"Tool Agent Error: {e}")

        return None
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_tool_agent.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add core/agent/tool_agent.py tests/test_tool_agent.py
git commit -m "feat(agent): registry-aware decide_tool returning ToolCall|None

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: `execute_tool` — generic registry dispatch

**Files:**
- Modify: `core/agent/tool_executor.py` (full rewrite)
- Test: `tests/test_tool_executor.py`

- [ ] **Step 1: Write the failing tests** `tests/test_tool_executor.py`

```python
from core.agent import tool_executor
from core.agent import registry


def test_dispatches_with_args():
    captured = {}

    @registry.tool("echo", "echo",
                   params={"msg": {"type": "str", "required": True}})
    def _echo(msg):
        captured["msg"] = msg
        return f"said {msg}"

    out = tool_executor.execute_tool(registry.ToolCall("echo", {"msg": "hi"}))
    assert out == "said hi"
    assert captured["msg"] == "hi"


def test_unknown_tool_returns_none():
    assert tool_executor.execute_tool(registry.ToolCall("nope", {})) is None


def test_handler_error_returns_message():
    @registry.tool("boom", "boom")
    def _boom():
        raise RuntimeError("kaboom")

    out = tool_executor.execute_tool(registry.ToolCall("boom", {}))
    assert out == "Tool execution failed."
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_tool_executor.py -v`
Expected: FAIL — old `execute_tool(tool)` takes a string and dispatches via `if/elif`, so `ToolCall(...)` and unknown-name handling break.

- [ ] **Step 3: Rewrite `core/agent/tool_executor.py`**

```python
from core.agent import (
    registry
)

from core.utils.logger import (
    logger
)


def execute_tool(call):

    spec = registry.get(call.name)

    if spec is None:

        logger.warning(f"No such tool: {call.name!r}")

        return None

    try:

        return spec.handler(**call.args)

    except Exception as e:

        logger.exception(f"Tool Execution Error: {e}")

        return "Tool execution failed."
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_tool_executor.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Verify the complexity warning is gone**

Run: `python -m flake8 core/agent/tool_executor.py --max-complexity=10`
Expected: no output (the C901 on `execute_tool` is resolved).

- [ ] **Step 6: Commit**

```bash
git add core/agent/tool_executor.py tests/test_tool_executor.py
git commit -m "refactor(agent): execute_tool is a generic registry dispatch

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Wire into `app.py` + fix the regression test

**Files:**
- Modify: `app.py` (3 edits)
- Modify: `tests/test_process_query.py` (1 edit)

- [ ] **Step 1: Add the loader import** to `app.py`. After the existing `from core.agent.tool_executor import (execute_tool)` block ([app.py:65-67](../../../app.py)), add:

```python
from core.agent.loader import (
    init_tools
)
```

- [ ] **Step 2: Call `init_tools()` once at startup.** In `main()` ([app.py:371-373](../../../app.py)), right after `logger.info("Starting Jarvis...")`, add:

```python
    init_tools()
```

(Safe to call early — registration has no OS side-effects; handlers lazy-import OS deps.)

- [ ] **Step 3: Update the dispatch block** in `process_query` ([app.py:172-184](../../../app.py)). Replace:

```python
    tool = decide_tool(query)

    if tool != "none":

        logger.info(f"Executed Tool: {tool}")

        response = execute_tool(tool)

        if response:

            speak(response)

        return
```

with:

```python
    call = decide_tool(query)

    if call is not None:

        logger.info(f"Executed Tool: {call.name} args={call.args}")

        response = execute_tool(call)

        if response:

            speak(response)

        return
```

- [ ] **Step 4: Fix the regression test.** In `tests/test_process_query.py:41`, change:

```python
    monkeypatch.setattr(app, "decide_tool", lambda q: "none")
```

to:

```python
    monkeypatch.setattr(app, "decide_tool", lambda q: None)
```

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest`
Expected: PASS — all prior 96 tests plus the new ones (≈108 total), 0 failures.

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_process_query.py
git commit -m "feat(agent): wire init_tools + ToolCall dispatch into the voice loop

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Example plugin + contract docs

**Files:**
- Create: `plugins/roll_dice.py`
- Create: `plugins/README.md`
- Test: `tests/test_loader.py` (add one test)

- [ ] **Step 1: Write the failing test** (append to `tests/test_loader.py`)

```python
def test_example_plugin_loads_from_repo(tmp_path):
    from core.paths import resource_dir
    loader.load_plugins([resource_dir() / "plugins"])
    spec = registry.get("roll_dice")
    assert spec is not None
    out = spec.handler(sides=6)
    assert "rolled" in out.lower()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_loader.py::test_example_plugin_loads_from_repo -v`
Expected: FAIL — `roll_dice` not registered (file doesn't exist yet).

- [ ] **Step 3: Create `plugins/roll_dice.py`**

```python
import random

from core.agent.registry import (
    tool
)


@tool(
    "roll_dice",
    "Roll an N-sided die",
    params={
        "sides": {
            "type": "int",
            "required": False,
            "default": 6,
            "desc": "number of sides",
        }
    },
)
def roll_dice(sides=6):

    return f"You rolled a {random.randint(1, sides)} on a {sides}-sided die."
```

- [ ] **Step 4: Create `plugins/README.md`**

```markdown
# Jarvis plugins

Drop a `*.py` file in this folder (or in `%APPDATA%\JarvisAI\plugins` when
running the packaged app) and Jarvis picks up its tools on the next launch —
no core edits required.

## Contract

A plugin is any module that registers one or more tools with the `@tool`
decorator:

```python
from core.agent.registry import tool

@tool(
    "roll_dice",                       # unique tool name (its words also act as
                                       # trigger keywords for the action gate)
    "Roll an N-sided die",             # description shown to the selector LLM
    params={                           # optional; omit for a parameterless tool
        "sides": {"type": "int", "required": False, "default": 6,
                  "desc": "number of sides"},
    },
)
def roll_dice(sides=6):
    return f"You rolled a {random.randint(1, sides)} on a {sides}-sided die."
```

- Supported param `type`s: `"str"`, `"int"`.
- The handler returns a short string Jarvis speaks back (or `None`).
- Files whose name starts with `_` are ignored.
- A plugin that raises on import is logged and skipped — it won't crash Jarvis.

## Trust

Plugins are **trusted local code** and run in Jarvis's own process — exactly
like an editor extension you choose to install. Only add plugins you trust.
```

- [ ] **Step 5: Run to verify it passes**

Run: `python -m pytest tests/test_loader.py -v`
Expected: PASS (loader tests including the new one).

- [ ] **Step 6: Commit**

```bash
git add plugins/roll_dice.py plugins/README.md tests/test_loader.py
git commit -m "feat(agent): example roll_dice plugin + plugin authoring docs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: Remove dead module, bundle plugins, full verification

**Files:**
- Delete: `core/agent/tool_registry.py`
- Modify: `jarvis.spec` (add plugins to `datas`)

- [ ] **Step 1: Confirm nothing imports the old flat registry**

Run: `rg -n "tool_registry|from core.agent.tool_registry|import TOOLS" --glob '*.py'`
Expected: the only hit is `core/agent/tool_registry.py` itself (Task 5 already removed the `from core.agent.tool_registry import (TOOLS)` line from `tool_agent.py`). If anything else references it, fix that first.

- [ ] **Step 2: Delete the file**

```bash
git rm core/agent/tool_registry.py
```

- [ ] **Step 3: Add `plugins/` to the frozen build.** In `jarvis.spec`, edit the `datas` list ([jarvis.spec:11-14](../../../jarvis.spec)):

```python
datas = [
    ("models", "models"),
    ("hud/web", "hud/web"),
    ("plugins", "plugins"),
]
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest`
Expected: PASS — ~108 tests, 0 failures.

- [ ] **Step 5: Build-breaking lint must be 0**

Run: `python -m flake8 . --select=E9,F63,F7,F82,F401 --exclude=venv,__pycache__,dist,build --count`
Expected: `0`.

- [ ] **Step 6: Confirm the complexity hotspot is gone**

Run: `python -m flake8 . --exit-zero --max-complexity=10 --max-line-length=127 --exclude=venv,__pycache__,dist,build`
Expected: `execute_tool` no longer appears; only pre-existing warnings remain (the `_start_hud` C901 and the test-file E731/F841 noted in the audit — those are out of scope here).

- [ ] **Step 7: Commit**

```bash
git add jarvis.spec
git commit -m "chore(agent): drop flat tool_registry; bundle plugins/ in the frozen build

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final state

- New: `core/agent/registry.py`, `core/agent/builtins.py`, `core/agent/loader.py`, `plugins/roll_dice.py`, `plugins/README.md`, `tests/conftest.py`, `tests/test_registry.py`, `tests/test_open_app.py`, `tests/test_loader.py`, `tests/test_tool_agent.py`, `tests/test_tool_executor.py`.
- Changed: `core/agent/tool_agent.py`, `core/agent/tool_executor.py`, `app.py`, `tests/test_process_query.py`, `jarvis.spec`.
- Removed: `core/agent/tool_registry.py`.
- The 6 original tools behave exactly as before; `open_app <name>` and the `roll_dice` plugin prove params + drop-in loading end-to-end; the `execute_tool` complexity-11 warning is gone; no new dependency.

## Spec coverage check

| Spec section | Covered by |
|---|---|
| §3 Module layout | Tasks 1, 3, 4, 5, 6, 9 |
| §4 Tool contract (ParamSpec/ToolSpec/ToolCall/@tool/validation) | Tasks 1, 2 |
| §5.1 Selector (registry-aware gate, prompt, balanced JSON, validate) | Task 5 |
| §5.2 Executor | Task 6 |
| §5.3 app.py integration + regression | Task 7 |
| §6 open_app exemplar (resolve_app split) | Task 3 |
| §7 Plugin loader (dirs, dedupe, missing-dir, broken-skip) + jarvis.spec datas | Tasks 4, 9 |
| §7 Example plugin + README | Task 8 |
| §8 Error handling (each row) | Tasks 4 (broken plugin), 5 (parse/validate/unknown), 6 (handler error), 1 (dup name) |
| §9 Testing (all rows) | Tasks 1–8 |
| §10 Success criteria | Task 7 (open notepad), Task 8 (roll dice no core edit), Task 9 (lint/complexity) |
