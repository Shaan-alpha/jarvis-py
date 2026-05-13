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

### v3.0.0 — Production release (shipped)

| Area | Status |
|---|---|
| Local LLM via Ollama (Phi-3) | done |
| Streaming token responses | done |
| Semantic memory + caching | done |
| Document RAG (FAISS) | done |
| Wake-word detection (openWakeWord) | done |
| Offline STT (Vosk) + Online STT (Google) with auto-fallback | done |
| Streaming TTS queue | done |
| Tool-agent + fast keyword router | done |
| One-shot reminders (threading.Timer) | done |
| Slim install — fastembed (ONNX), no torch/transformers | done |
| User profile-driven context | done |
| Structured logging | done |

### Release history

| Tag | Theme |
|---|---|
| v2.0.0 | Initial modular architecture |
| v2.1.0 | Tool agent + memory caching stability pass |
| v2.2.0 | Real `hey jarvis` wake word |
| v2.3.0 | Hybrid online/offline STT |
| v2.4.0 | Lean install + faster routing + accurate reminders |
| v3.0.0 | fastembed swap, lazy wake-word, production-ready |

---

## v3.1 — Polish & Packaging

Goal: ship-ready binary you can hand someone.

- [ ] `pyproject.toml` + `__init__.py` files for clean packaging
- [ ] PyInstaller spec for a single-file Windows build
- [ ] Bundle Vosk + wake-word ONNX into the package
- [ ] Smoke-test workflow in CI (GitHub Actions, Windows runner)
- [ ] First-run setup wizard (profile, Ollama model pull)
- [ ] Auto-detect microphone + permissions
- [ ] Crash-recovery: re-launch on TTS/STT exceptions

---

## v3.2 — Agent Capabilities

Goal: make the tool-agent useful for real tasks, not just demos.

- [ ] Tool-agent supports multi-step plans (e.g. "open VS Code and start the dev server")
- [ ] File-system tools: read/write/search files in a sandboxed root
- [ ] Clipboard tool (read + write)
- [ ] Screenshot tool (capture + OCR via local model)
- [ ] Window control (focus, minimize, list windows)
- [ ] Browser automation via Playwright (search, open, scrape)
- [ ] Plugin loader — drop a Python file in `plugins/`, get a new tool

---

## v3.3 — Smarter Memory

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

| Surface | Stack candidate |
|---|---|
| Desktop shell | Tauri + React + Tailwind |
| Voice orb + waveform | Canvas / Lottie |
| Real-time channel | WebSockets to a local FastAPI |
| Subtitles / streaming | Server-sent events |

Features:
- Animated wake-word orb
- Live subtitles for both user and Jarvis
- Memory dashboard (search + edit memories)
- Document drop zone (PDFs → auto-index)
- Reminder list + edit
- Conversation history panel
- Floating overlay / command palette

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
