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
USER SPEAKS
    │
    ▼
Wake-word detection (openWakeWord, ONNX)        core/speech/openwakeword_listener.py
    │  "hey jarvis" > WAKE_THRESHOLD
    ▼
Speech-to-text                                  core/speech/engine.py
    ├─ online?  → Google STT                    core/speech/online_recognizer.py
    └─ offline  → Vosk (auto-fallback)          core/speech/offline_recognizer.py
    │
    ▼
clean_query() → lowercase / strip punctuation   core/speech/engine.py
    │
    ▼
ROUTING (first match wins)                       app.py main loop
    ├─ exit words ("bye", "exit", ...)          → sleep
    ├─ profile capture ("my name is ...")       core/memory/profile_extractor.py
    ├─ reminder ("remind me in N minutes ...")  core/tasks/task_parser.py
    ├─ fast keyword router (app/media/browser/  core/router/intent_router.py
    │    system intents)                        core/intents/*
    ├─ action-verb gate → LLM tool agent        core/agent/tool_agent.py
    │    └─ execute_tool()                      core/agent/tool_executor.py
    └─ LLM chat fallback (Ollama, streaming)    core/ai/ollama_engine.py
    │
    ▼
Streaming sentence-level TTS queue (serialized)  core/speech/tts_queue.py
    │
    ▼
pyttsx3 speak                                    core/speech/engine.py
    ▲
    │  barge-in: a HUD Stop button / Esc / a newly typed query cancels the
    │  current utterance + clears the queue (ask_llm carries a generation token
    │  so a superseded stream aborts). "hey jarvis" mid-speech also works but is
    └─ unreliable over the speakers (no echo cancellation).  tts_queue / app.py
```

---

## Module map

| Package | Responsibility |
|---|---|
| `core/speech/` | Wake-word detection, online/offline STT, TTS engine + serialized queue, online/offline connectivity check |
| `core/ai/` | Ollama LLM client with streaming token output and prompt assembly |
| `core/router/` | Fast keyword → intent-handler routing (the cheap path) |
| `core/intents/` | Intent handlers: app control, media control, browser, system status |
| `core/agent/` | LLM tool agent (selects a tool), tool registry (the catalog), tool executor (runs it) |
| `core/memory/` | fastembed embedder, semantic conversation memory, document RAG (FAISS), user-profile store + extractor |
| `core/tasks/` | Reminder parsing, `threading.Timer`-backed scheduling, JSON persistence |
| `core/state/` | Session lifecycle + silence timeout |
| `core/automation/` | OS-level actions (open/close apps, system status) |
| `core/commands/` | Browser/search helpers |
| `core/utils/` | Structured logger, greeting/date helpers |
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

- **Add a deterministic command:** add keywords to
  [`core/router/intent_router.py`](../core/router/intent_router.py) and a handler
  under `core/intents/`.
- **Add an LLM-selectable tool:** decorate a function with `@tool(...)` in
  [`core/agent/builtins.py`](../core/agent/builtins.py), or drop a `*.py` plugin in
  [`plugins/`](../plugins/). The decorator registers it via
  [`core/agent/registry.py`](../core/agent/registry.py); `decide_tool`
  ([`core/agent/tool_agent.py`](../core/agent/tool_agent.py)) then offers it to the
  model and `execute_tool()`
  ([`core/agent/tool_executor.py`](../core/agent/tool_executor.py)) dispatches the call.
- **Tune behavior:** every threshold and path lives in
  [`config/settings.py`](../config/settings.py).
