# JARVIS-PY ROADMAP

> From a Python voice assistant to a full AI-powered desktop operating companion.

---

## Vision

Build a modular AI desktop assistant inspired by Iron Man's JARVIS.

The system should:
- Work online and offline
- Understand voice commands
- Use local and cloud LLMs
- Control the operating system
- Execute multi-step tasks
- Remember conversations and documents
- Support plugins and APIs
- Have a modern futuristic UI
- Be deployable as a desktop application

---

## Core Philosophy

The project evolves in layers:

1. Intelligence
2. Offline capability
3. Automation
4. UI/UX polish
5. Deployment ecosystem

Architecture first. No giant single files.

---

## Current Status

> Latest release: **v3.3.0 "Polish & Packaging"** (+ a HUD overhaul: fluid-blob
> orb, Stop/Esc interrupt, wake-word + STT fixes) — **shipped**: merged to `main`,
> tagged `v3.3.0`, GitHub Release published (2026-05-31, *Latest*). 129 tests green;
> `pyproject`/`CHANGELOG` at 3.3.0 match the published version. **v3.4 — Agent
> Capabilities is underway:** the Layer-1 tool foundation (tool registry + `@tool`
> decorator + plugin loader, PR #4) and the routing unification (registry is the
> single source of truth, PR #6) are merged to `main`. **Layer 2 — capability
> tools — has started:** clipboard read/write (the first capability tool) is in
> review (PR #7). Next capability tools + orchestration are below.

### v3.2.0 — Desktop HUD (shipped)

The "Iron Man Interface" arrived early and with a different stack than v4.0
originally sketched: an optional always-on-top desktop panel (`python app.py
--hud`) built with **pywebview + vanilla HTML/CSS/JS** (not Tauri/React),
talking to the Python core over a local WebSocket. Animated state orb, live
mic waveform, streaming captions (user + Jarvis), type-to-Jarvis input, live
status row, and a time-adaptive theme (cyan/gold/frost). Core is byte-for-byte
unchanged without the flag. This delivers much of v4.0's orb/waveform/subtitles
goals — see v4.0 below for what remains.

### v3.1.0 — Interactive UX (shipped)

| Area | Status |
|---|---|
| Local LLM via Ollama (Phi-3) | done |
| Streaming token responses | done |
| Semantic memory + caching | done |
| Document RAG (FAISS) + similarity threshold | done |
| Wake-word detection (openWakeWord) | done |
| Wake-word **barge-in** during TTS playback | done |
| Offline STT (Vosk) + Online STT (Google) with auto-fallback | done |
| Streaming TTS queue (serialized, no collisions) | done |
| Tool-agent + fast keyword router + action-verb gate | done |
| One-shot reminders (threading.Timer) | done |
| Slim install — fastembed (ONNX), no torch/transformers | done |
| User profile-driven context | done |
| Structured logging | done |
| Privacy-clean repo (no user data, no bundled models) | done |

### Release history

| Tag | Theme |
|---|---|
| v2.0.0 | Initial modular architecture |
| v2.1.0 | Tool agent + memory caching stability pass |
| v2.2.0 | Real `hey jarvis` wake word |
| v2.3.0 | Hybrid online/offline STT |
| v2.4.0 | Lean install + faster routing + accurate reminders |
| v3.0.0 | fastembed swap, lazy wake-word, production-ready |
| v3.1.0 | Wake-word barge-in, doc-RAG threshold, repo privacy |
| v3.2.0 | Desktop HUD (pywebview + local WebSocket); audit hardening |
| v3.3.0 | Polish & Packaging — Windows one-folder build, setup wizard, crash-recovery |

---

## v3.3 — Polish & Packaging (shipped as v3.3.0)

Goal: ship-ready binary you can hand someone.

- [x] `pyproject.toml` + `__init__.py` files for clean packaging
- [x] PyInstaller spec for a Windows build (`jarvis.spec`, one-folder — not single-file)
- [x] Bundle Vosk + wake-word ONNX into the package (`datas` in `jarvis.spec`)
- [x] Smoke test (manual, documented in README/PR — **not** CI; no Windows runner)
- [x] First-run setup wizard (profile, Ollama model pull, prerequisite checks)
- [x] Auto-detect microphone
- [x] Crash-recovery: TTS re-init + graceful degradation (Ollama down, no mic, model-load fail)
- All paths resolve via `core/paths.py` (`resource_dir()` / `user_data_dir()`)

> Done: manual Windows build + smoke test, merged to `main`, tagged **v3.3.0**,
> GitHub Release published (2026-05-31).

---

## v3.4 — Agent Capabilities

Goal: make the tool-agent useful for real tasks, not just demos.

Layer 1 (foundation) and the routing unification are shipped to `main`; Layer 2
(capability tools) is in progress.

- [x] **Layer 1 — tool foundation**: registry + `@tool` decorator + arg
  coercion/validation + `builtins` module (PR #4)
- [x] **Plugin loader** — drop a Python file in `plugins/` (or
  `%APPDATA%\JarvisAI\plugins`), get a new tool (PR #4)
- [x] **Routing unification** — the registry is the single source of truth;
  `decide_tool`/`execute_tool` dispatch generically (PR #6)
- [x] **Clipboard tool (read + write)** — first Layer-2 capability; `read_clipboard`
  has a keyword fast-path, `write_clipboard` is LLM-only (PR #7, in review)
- [ ] File-system tools: read/write/search files in a sandboxed root
- [ ] Screenshot tool (capture + OCR via local model)
- [ ] Window control (focus, minimize, list windows)
- [ ] Browser automation via Playwright (search, open, scrape)
- [ ] Tool-agent supports multi-step plans (e.g. "open VS Code and start the dev server")

---

## v3.5 — Smarter Memory

Goal: memory that gets better over time.

- [ ] Hybrid retrieval: BM25 (fastembed has it) + dense, then re-rank
- [ ] Auto-summarize long conversation chains into long-term memory
- [ ] Per-topic memory partitioning
- [ ] Memory decay / pruning policy
- [ ] Document re-index watcher (auto-rebuild when `data/documents/` changes)
- [ ] Source citations in LLM answers (which chunk → which file)

---

## v4.0 — Iron Man Interface

Goal: a real UI, not a terminal.

> **Partly shipped in v3.2.0.** The HUD chose **pywebview + vanilla JS over a
> local WebSocket** instead of the Tauri/React/FastAPI stack originally sketched
> here — no Rust+Node toolchain. The orb, live waveform, and dual subtitles are
> done. What remains is the data-management UI below.

Stack (as built):

| Surface | Stack (shipped) |
|---|---|
| Desktop shell | pywebview window |
| Voice orb + waveform | Canvas |
| Real-time channel | WebSocket to the Python core |
| Subtitles / streaming | WebSocket events |

Features:
- [x] Animated wake-word orb
- [x] Live subtitles for both user and Jarvis
- [x] Floating overlay (always-on-top panel) + type-to-Jarvis input
- [ ] Memory dashboard (search + edit memories)
- [ ] Document drop zone (PDFs → auto-index)
- [ ] Reminder list + edit
- [ ] Conversation history panel
- [ ] Command palette

---

## v5.0 — Deployment

Goal: production distribution.

- [ ] Cross-platform builds (Win / macOS / Linux)
- [ ] Auto-update channel via GitHub Releases
- [ ] Code signing (Windows + macOS)
- [ ] Telemetry-opt-in usage metrics (local only)
- [ ] Documentation site (Mintlify / Docusaurus)
- [ ] Demo landing page with videos

---

## Future Experiments

- Voice cloning (custom Jarvis voice)
- Emotion detection from voice tone
- Smart routines ("good morning" → schedule + weather + workspace)
- AR / heads-up display surface
- AI coding assistant tool integration
- Webcam vision + OpenCV

---

## Final Mission

> A modular AI desktop operating assistant capable of voice interaction,
> offline intelligence, memory, automation, multimodal interaction, and
> futuristic system control.

Not a chatbot. An ecosystem.

---

## Motto

Build the engine first. Then build the armor.
