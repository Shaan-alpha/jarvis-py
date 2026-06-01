# Agent Tool Foundation — Design Spec

- **Date:** 2026-06-01
- **Status:** Draft for review
- **Owner:** Shaan Satsangi
- **Milestone:** v3.4 — Agent Capabilities (Layer 1 of 3; ships as the v3.4.0 foundation)
- **Feature:** Replace the flat, parameterless tool-agent with a parameterized tool
  protocol, a real registry, and a drop-in plugin loader — the keystone every other
  v3.4 capability (file-system, clipboard, window control, screenshot, browser,
  multi-step plans) builds on.

---

## 1. Summary

Today the tool-agent ([`core/agent/`](../../../core/agent/)) is a flat dict of **6
parameterless tools** dispatched through a hardcoded `if/elif` chain. It cannot pass
arguments ("open **notepad**", "read **file X**"), cannot chain steps, and adding a
tool means editing two files. The selector returns a bare tool name; the executor is
a growing `if/elif` (the `execute_tool` function the post-release audit flagged at
flake8 complexity 11).

This spec defines the **foundation** that unblocks the rest of v3.4:

1. A **parameterized tool protocol** — tools declare a small typed args schema; the
   LLM selector returns `{"tool", "args"}`; args are validated/coerced before
   dispatch.
2. A **real registry** — tools register as callables (`@tool(...)` decorator)
   carrying their description + args schema. The `if/elif` executor becomes a generic
   registry lookup (removing the complexity-11 hotspot).
3. A **plugin loader** — drop a `*.py` file in a `plugins/` directory and its
   decorated tools self-register on import. No core edits required.

To prove the protocol end-to-end, the slice also ships **one parameterized built-in
tool** (`open_app <name>`) and **one example drop-in plugin** (`roll_dice`).

The change is a **strict superset of today's behavior**: the 6 existing tools keep
identical behavior; everything new is additive.

### Non-goals (this slice)

Explicitly **deferred** to later v3.4 sub-projects, not built here:

- Multi-step plans / tool chaining (Layer 3 orchestration).
- The capability tools themselves beyond the `open_app` exemplar — clipboard,
  sandboxed file-system, window control, screenshot+OCR, browser automation
  (Layer 2).
- A conversational **clarification loop** ("which app?") when a required arg is
  missing — for now that degrades to normal chat.
- Plugin sandboxing / permissions / a marketplace — plugins are trusted local code
  (see §7).
- Rich arg types — only `str` and `int` are supported in this slice.

---

## 2. Constraints

- **Free / local / zero-money.** No paid APIs or services. Validation is **stdlib
  only** — no pydantic or other new heavy dependency.
- **Windows-first.** `open_app` targets Windows app launching. The protocol/registry/
  loader are OS-portable.
- **CI-safe.** No test may need a mic, display, network, or a model download.
  `core/agent/builtins.py` must be importable on headless CI: decorators only
  *define* tools at import; OS deps (`pyautogui`) are lazy-imported **inside** the
  handler that needs them.
- **Frozen-build safe.** `init_tools()` must run for both `python app.py` and the
  PyInstaller build; plugin directories resolve via `core.paths`
  (`resource_dir()` + `user_data_dir()`), never CWD-relative paths.
- **Degrade, never crash.** Any malformed model output, bad arg, unknown tool, or
  broken plugin falls back to normal behavior with a log line — never an exception
  to the user.
- **Match house code style.** `core/**` idiom (blank line between statements,
  grouped imports); line length ≤ 127; complexity ≤ 10.

---

## 3. Module layout

| File | Role | Fate |
|---|---|---|
| `core/agent/registry.py` | `@tool` decorator, `ParamSpec`/`ToolSpec`/`ToolCall` dataclasses, the process-wide registry, and stdlib arg validation/coercion. Single source of truth. | **new** |
| `core/agent/builtins.py` | The 6 existing tools migrated to decorated functions + the new `open_app` (incl. its pure `resolve_app` resolver). Replaces the `if/elif` body. | **new** |
| `core/agent/loader.py` | `init_tools()` → `load_builtins()` + `load_plugins(dirs)`; imports plugin modules so their decorators self-register. | **new** |
| `core/agent/tool_agent.py` | `decide_tool(query)` builds its prompt from the registry and returns `ToolCall \| None`. Keeps the action-verb gate; brace-balanced JSON extraction. | edit |
| `core/agent/tool_executor.py` | `execute_tool(call)` → registry lookup + `handler(**args)`. ~10 lines; kills complexity-11. | edit |
| `core/agent/tool_registry.py` | Flat `TOOLS` dict superseded by `registry.py`. | **delete** |
| `app.py` | `"none"` sentinel → `None`; call `init_tools()` once at startup. | edit |
| `plugins/roll_dice.py` + `plugins/README.md` | Example drop-in plugin + the contract docs. | **new** |
| `tests/test_*` | New CI-safe tests + one regression edit (`test_process_query.py`). | new/edit |

---

## 4. The tool contract (data model)

```python
# core/agent/registry.py  (stdlib only)
@dataclass(frozen=True)
class ParamSpec:
    type: str            # "str" | "int"  (only these two this slice)
    required: bool = True
    desc: str = ""
    default: object = None

@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    params: dict[str, ParamSpec]      # {} for the parameterless tools
    handler: Callable[..., str | None]

@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict[str, object]
```

- `@tool(name, description, params=None)` builds a `ToolSpec` and registers it.
  `params` is a plain dict (`{"name": {"type": "str", "required": True, "desc": ...}}`)
  coerced into `ParamSpec`s, so plugin authors never import internal classes beyond
  the decorator.
- Duplicate name → last registration wins + `logger.warning`.
- Registry API: `get(name) -> ToolSpec | None`, `all_tools() -> list[ToolSpec]`,
  `clear()` (test reset only).
- `coerce_and_validate(spec, raw_args) -> tuple[dict, str | None]`:
  - coerce each declared param by `type` (`"int"` → `int(x)`, `"str"` → `str(x)`),
  - fill `default` for a missing optional param,
  - **return an error string** if a required param is missing or uncoercible,
  - **drop unknown keys** the model hallucinated.

Handlers stay thin and return a short user-facing string (or `None`). OS deps are
lazy-imported inside the handler body.

---

## 5. Request flow

### 5.1 Selector — `decide_tool(query) -> ToolCall | None`

(was `-> str`, returning a name or the `"none"` sentinel)

1. **Registry-aware gate:** `_looks_like_action(query)` short-circuits non-commands
   to `None` (avoids an LLM round-trip for chit-chat). A query passes if it starts
   with a built-in `ACTION_VERB` **or shares a word with any registered tool's name**
   (e.g. `roll_dice` → `{roll, dice}`, so "roll a dice" passes). A dropped plugin thus
   gates itself via its name — **no core edit needed**, satisfying §10. Trade-off: a
   few extra chit-chat queries may reach the LLM selector, which safely returns
   `none`; over-triggering the gate never causes a wrong action.
2. **Prompt built from the registry:** each tool is rendered with its name,
   description, **and its params** (name / type / required / desc). Output contract:
   ```json
   {"tool": "open_app", "args": {"name": "notepad"}}
   ```
   or `{"tool": "none"}`. The prompt includes a parameterized example
   (`"open notepad" → open_app{name:notepad}`) and `none` examples (questions /
   chitchat), mirroring the existing strict-selector style.
3. **Robust parse:** the current extractor `re.search(r"\{[^{}]*\}")` **cannot match
   nested objects** and would break on `"args": {...}`. Replace it with a
   brace-balancing scan from the first `{` (or `json.JSONDecoder().raw_decode`).
   Stdlib only.
4. **Validate or fall through:** unknown / `none` / missing tool → `None`. Otherwise
   run `coerce_and_validate`; on error → **log + return `None`** (request falls
   through to normal LLM chat — no clarification loop this slice).
5. Returns `ToolCall(name, validated_args)`.

The phi3-reliability risk lives entirely here and degrades safely: malformed or
uncertain output → `None` → the user just gets a normal answer.

### 5.2 Executor — `execute_tool(call: ToolCall) -> str | None`

```python
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

### 5.3 `app.py` integration

Minimal churn at [`app.py:172`](../../../app.py) — `"none"` sentinel becomes `None`:

```python
call = decide_tool(query)
if call is not None:
    logger.info(f"Executed Tool: {call.name} args={call.args}")
    response = execute_tool(call)
    if response:
        speak(response)
    return
```

`init_tools()` is called once during startup (alongside the other init in
`app.main()`), for both dev and frozen runs.

---

## 6. Built-in `open_app <name>` (the exemplar)

Resolution is split from the side-effect for testability:

- `resolve_app(name: str) -> str` — **pure function.** A small alias table
  (`notepad`, `calculator`→`calc`, `spotify`→`spotify:`, `chrome`, …); unknown names
  pass through unchanged to the shell launcher. **Unit-tested.**
- Launch via `os.startfile` / `subprocess` `start` — the side-effect, **mocked in
  tests.**

The 6 existing tools (`open_calculator`, `open_youtube`, `open_google`,
`increase_volume`, `decrease_volume`, `mute_volume`) are migrated as decorated
functions with **identical behavior**. Folding `open_calculator` into `open_app` is a
later cleanup, not part of this slice.

---

## 7. Plugin loader

```python
# core/agent/loader.py
def init_tools() -> None:           # called once at startup
    load_builtins()                 # import core.agent.builtins -> decorators fire
    load_plugins(_plugin_dirs())    # resource_dir()/plugins + user_data_dir()/plugins

def load_plugins(dirs) -> None:
    for d in dirs:
        for path in sorted(d.glob("*.py")):       # skip names starting with "_"
            try:
                _import_file(path)                 # importlib spec_from_file_location + exec_module
            except Exception as e:
                logger.exception(f"Skipping bad plugin {path}: {e}")
```

- **Path resolution via `core.paths`:** bundled examples under `resource_dir()/plugins`
  and user drop-ins under `user_data_dir()/plugins` — works frozen. A directory that
  doesn't exist is simply skipped (no error).
- **Frozen build:** `jarvis.spec` must add `plugins/` to `datas` so the bundled
  example ships under `_internal/plugins`; otherwise it won't be found in the `.exe`.
- **Trust model (documented in `plugins/README.md`):** plugins are *trusted local
  Python*, like an editor extension you choose to install. This is a single-user local
  app; plugins run in-process. A broken plugin is logged and **skipped**, never fatal.
- **Idempotent:** `init_tools()` is safe to call once; re-registration warns.

### Example plugin — `plugins/roll_dice.py`

Proves params **and** a default via the drop-in path:

```python
from core.agent.registry import tool
import random

@tool("roll_dice", "Roll an N-sided die",
      params={"sides": {"type": "int", "required": False, "default": 6,
                        "desc": "number of sides"}})
def roll_dice(sides: int = 6) -> str:
    return f"You rolled a {random.randint(1, sides)} on a {sides}-sided die."
```

`plugins/README.md` documents this ~4-line contract.

---

## 8. Error handling (degrade, never crash)

| Failure | Behavior |
|---|---|
| Malformed / uncertain LLM JSON | `decide_tool → None` → normal chat |
| Required arg missing / bad type | validation fails → `None` → normal chat (logged) |
| Unknown tool name from model | `None` |
| Handler raises at runtime | caught → `"Tool execution failed."` spoken |
| Broken plugin file | logged + skipped at load; app starts normally |
| Duplicate tool name | last registration wins + `logger.warning` |

---

## 9. Testing (all CI-safe — no mic / display / network / model)

- **registry:** register / lookup / `all_tools` / `clear`; `coerce_and_validate` —
  int coercion, default fill, required-missing → error, unknown-key drop.
- **decide_tool:** monkeypatch `requests.post` to return canned Ollama JSON → assert
  `ToolCall(name, args)` for a parameterized command, `None` for a question, `None`
  for invalid args. (No real model/network.)
- **execute_tool:** register a fake tool → assert dispatch + args passed;
  handler-raises → `"Tool execution failed."`; unknown name → `None`.
- **loader:** import a temp plugin file from `tmp_path` → registers; a deliberately
  broken file → skipped without raising.
- **open_app:** `resolve_app` aliases / pass-through asserted; launch side-effect
  mocked.
- **regression:** update `test_process_query.py` (`decide_tool` returns `None`, not
  `"none"`).

Target: ~12–15 new tests; suite stays green; the `execute_tool` complexity-11
warning is gone.

---

## 10. Success criteria

- "open notepad" launches Notepad via the parameterized `open_app` tool (args flow
  end-to-end).
- Dropping `plugins/roll_dice.py` makes "roll a dice" work with **no core edits**.
- The 6 original tools behave exactly as before.
- `flake8 --select=E9,F63,F7,F82,F401` stays 0; `execute_tool` no longer trips the
  C901 complexity warning.
- Full test suite green on CI; no new runtime dependency added.

---

## 11. Out of scope / follow-on (the rest of v3.4)

- **Layer 2 — capability tools:** clipboard, sandboxed file-system, window control,
  screenshot+OCR, browser automation (Playwright). Each is "just another registered
  tool" on this foundation.
- **Layer 3 — orchestration:** multi-step plans that chain several tool calls from a
  single request.
- Arg clarification loop, richer arg types (lists/enums/floats), plugin
  permissions/sandboxing.
