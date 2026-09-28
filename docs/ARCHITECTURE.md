# Jarvis Architecture

## Overview

Jarvis is a modular, local-first AI voice assistant built with Python. The
design goal is to evolve from a single-loop voice assistant into a scalable,
offline-capable AI desktop companion — without giant single files.

Every responsibility lives in its own `core/` subpackage, wired together by the
main loop in [`app.py`](../app.py).

---

## Request lifecycle

```text
USER SPEAKS  (or types in the HUD)
    │
    ▼
Wake-word detection (openWakeWord, ONNX)        core/speech/openwakeword_listener.py
    │  "hey jarvis" > WAKE_THRESHOLD
    ▼
Speech-to-text (raw text)                       core/speech/engine.py
    ├─ online?  → Google STT                    core/speech/online_recognizer.py
    └─ offline  → Vosk (auto-fallback)          core/speech/offline_recognizer.py
    │
    ▼
normalize() — same for voice and typed input    core/text.py
    │
    ▼
process_query (first match wins)                app.py
    ├─ pending confirmation? yes / no           core/state/conversation.py
    ├─ "repeat that" / "tell me more"           core/state/conversation.py
    ├─ profile capture ("i live in ...")        core/memory/profile_extractor.py
    ├─ reminder ("remind me in N minutes ...")  core/tasks/task_parser.py
    ├─ deterministic router → registry ToolCall core/router/intent_router.py
    │    memory · files · apps · info · maths · system · local search ·
    │    web search · weather · lookup           (router-only tools: llm=False)
    ├─ action-verb gate → LLM tool agent        core/agent/tool_agent.py
    │    └─ both converge on execute_tool()     core/agent/tool_executor.py
    │       (a tool returning None, e.g. a lookup miss, falls through)
    └─ grounded LLM chat (Ollama, streaming,    core/ai/ollama_engine.py
         date/time + online state + relevant facts/documents + last 3 turns,
         hard two-sentence cap; skipped at once while llm_health says down)
    │
    ▼
respond(): HUD caption + TTS queue               core/speech/reply.py
    │
    ▼
Serialized sentence-level TTS queue → pyttsx3    core/speech/tts_queue.py, engine.py
    ▲
    │  barge-in: Stop / Esc / a newly typed query → cancel_generation() +
    │  stop_speaking() + clear_queue(). "hey jarvis" mid-speech also works but is
    └─ unreliable over the speakers (no echo cancellation).
```

---

## Module map

| Package | Responsibility |
|---|---|
| `core/speech/` | Wake-word detection, online/offline STT, TTS engine + serialized queue, `reply.respond()` (one path for every spoken + shown reply) |
| `core/ai/` | Ollama client: grounded `build_prompt`, streaming with a hard sentence cap, `cancel_generation`; `llm_health` (fast path while the model is down) |
| `core/router/` | Deterministic routing — `resolve_keyword_tool()` runs an ordered list of matchers (memory, files, apps, info, maths, system, search, weather, lookup) and returns a registry `ToolCall` |
| `core/agent/` | Tool registry + `@tool(..., llm=False)` decorator, tool modules (`builtins`, `fs_tools` + `known_folders`, `info_tools`, `calc_tools`, `memory_tools`, `web_tools`, `search_tools`), plugin loader, LLM tool agent, executor |
| `core/memory/` | fastembed embedder, explicit facts store (`facts.py`), document RAG (FAISS + manifest, JSON chunks), user-profile store + extractor |
| `core/tasks/` | Reminder parsing, `threading.Timer`-backed scheduling, JSON persistence |
| `core/state/` | Session lifecycle + silence timeout; in-RAM `conversation` (last 3 turns, last file results, pending confirmations) |
| `core/utils/` | Structured logger, greeting/date helpers |
| `core/text.py`, `core/calc.py`, `core/net.py` | Stdlib helpers: input normalizer + spoken times/filenames; offline arithmetic (AST whitelist); connectivity check |
| `core/paths.py` | Path resolver: `resource_dir()` (bundled assets, → `sys._MEIPASS` when frozen) / `user_data_dir()` (writable, → `%APPDATA%\JarvisAI` when frozen). Stdlib-only |
| `core/setup/` | First-run checks (Ollama/model/mic/WebView2), mic auto-detect, streamed `pull_model`, `is_first_run()` — backs the HUD setup wizard |
| `core/hud/` + `hud/` | **Optional** desktop HUD — event bus, WebSocket server, stats/theme emitter (Python) + a pywebview-hosted vanilla-web panel (fluid-blob orb, captions, Stop button). Auto-opens on first run; otherwise active only with `python app.py --hud`. The core is untouched without it |
| `config/` | Central `settings.py` — all tunables in one place |

---

## Design principles

1. **Layered routing, cheapest first.** Deterministic keyword routing runs
   before any LLM call; the tool agent is gated behind an action-verb check so
   casual questions never trigger an unnecessary LLM hop.
2. **Local-first.** Embeddings (fastembed/ONNX), wake-word (ONNX), offline STT
   (Vosk) and the LLM (Ollama) all run on-device. Online services are an
   optional accelerator, not a dependency.
3. **Lazy, cached models.** Wake-word, Vosk, and embedding models load on first
   use and are cached; memory/document embeddings are cached and invalidated on
   write.
4. **No giant files.** Each concern is a small, independently testable module.

---

## Extending the assistant

- **Add a tool:** decorate a function with `@tool(...)` in
  [`core/agent/builtins.py`](../core/agent/builtins.py), or drop a `*.py` plugin in
  [`plugins/`](../plugins/). The decorator registers it via
  [`core/agent/registry.py`](../core/agent/registry.py); `decide_tool`
  ([`core/agent/tool_agent.py`](../core/agent/tool_agent.py)) then offers it to the
  model and `execute_tool()`
  ([`core/agent/tool_executor.py`](../core/agent/tool_executor.py)) dispatches the call.
  That single registration makes it reachable by the LLM tool agent automatically.
- **Add an instant keyword fast path (optional):** add a phrase + a branch returning
  the tool's `ToolCall` to
  [`core/router/intent_router.py`](../core/router/intent_router.py). The registry is
  the single source of truth; the keyword router is only a deterministic accelerator
  that skips the LLM hop for known phrases.
- **Tune behavior:** every threshold and path lives in
  [`config/settings.py`](../config/settings.py).
