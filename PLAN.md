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

> Latest release: **v3.4.0 "Agent Capabilities & Hardening"** — shipped, tagged,
> GitHub Release published. It bundled the Layer-1 tool foundation (PR #4),
> routing unification (PR #6), clipboard tools (PR #7), sandboxed file-system
> tools (PR #9), and the deep audit-hardening pass (findings F1–F15: security,
> crash-safe persistence, memory perf, NLU, content fidelity, TTS, cleanup).
>
> **v3.5 — Responsiveness & Efficiency is underway on `main` (unreleased).**
> Merged: latency instrumentation + `decide_tool` generation cap (PR #11),
> persistent-engine TTS reuse (PR #12), the model bake-off benchmark script
> (PR #13), and warm-start preload of the LLM + embedder (PR #14). **258 tests
> pass; lint clean.** Remaining v3.5 work: STT/wake stage marks + a HUD latency
> readout, wider deterministic keyword routing, STT tuning, and picking a faster
> default model from the bake-off (needs a run on the user's machine).
>
> **Roadmap direction: speed-first.** The guiding motto is *offline + online, but
> efficient and fast to respond*. v3.5 establishes a measured baseline; agent
> capabilities, smarter memory, the UI panels, and distribution each follow on
> top of a faster, measured core. See the sequenced milestones below.

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

## Cross-cutting guardrails (every milestone)

These hold for all work below — they are the project's identity, not a milestone:

- **Free / local / zero-money.** No paid APIs, no cloud services, no paid signing.
- **Offline + online parity.** Online is an enhancement, never a requirement; every
  capability must degrade gracefully offline.
- **Latency budget.** Once v3.5 establishes a measured baseline, no later milestone
  may regress it. New features are judged against the stage timings.
- **CI stays green.** Public adoption signal; keep tests + lint passing.

---

## v3.4.0 — Release the pending work (do first)

Goal: a clean, tagged baseline before the speed work starts.

- [x] Clipboard tools (PR #7) + sandboxed file-system tools (PR #9) — on `main`
- [x] Merge the audit-hardening pass (`fix/audit-2026-06-17`, F1–F15)
- [x] Bump `pyproject` + `CHANGELOG` to **3.4.0**, tag, publish a GitHub Release
      (the project's always-tag-and-release habit)

> The remaining "agent capability" tools originally filed under v3.4
> (screenshot/window/browser/multi-step) move **after** the speed milestone — see
> v3.6. They inherit the faster routing built in v3.5.

---

## 🏎️ v3.5 — Responsiveness & Efficiency  ← immediate focus

Goal: make Jarvis *feel* instant — measured, not guessed — without giving up
offline. This is the motto milestone.

- [~] **Latency instrumentation (do first)** — time each pipeline stage
      (wake → listen → STT → route → first-token → first-audio → done), log it,
      surface in the HUD. Every later change is judged against these numbers.
      *Done (PR #11):* `core/utils/metrics.py` `Timeline` + thread-local API,
      wired for the `routed`/`first_token`/`first_audio`/`done` stages. Remaining:
      STT/wake marks (voice-loop + HUD entry) and the HUD readout.
- [x] **TTS engine reuse** (PR #12) — each speaking thread owns a persistent
      `pyttsx3` engine in thread-local storage and reuses it across streamed
      sentences instead of `create_engine()` per sentence
      (`core/speech/engine.py`). Failure path drops + re-inits, keeping the old
      crash recovery. *(Needs a real-device smoke test for cross-thread stop.)*
- [x] **Warm-start** (PR #14) — a daemon thread preloads Ollama (priming ping)
      and the embedder at startup off the critical path so the first real query
      isn't cold (`core/warmup.py`). Best-effort per step. Vosk + openWakeWord are
      intentionally not warmed (may be unused / would race the native load).
- [~] **Faster tool routing** — *Done (PR #11):* `decide_tool` caps the Ollama
      call (`num_predict=80`, `temperature=0`) so its JSON returns fast. Remaining:
      widen the deterministic keyword path so common commands never hit the LLM;
      evaluate folding selection into the main streamed call.
- [ ] **STT tuning** — calibrate ambient noise once per session (not every
      listen), adaptive `pause_threshold`, optional Vosk partial results; optionally
      race online + offline STT and take the first good result (pure motto).
- [~] **Model bake-off** — *Done (PR #13):* `model_bakeoff.py` benchmarks `phi3`
      vs `phi3.5` / `llama3.2:3b` / `qwen2.5:1.5b` on tool-JSON accuracy + chat
      latency. Remaining: run it on the user's machine, pick a faster default,
      document the swap. Stays local/offline.

---

## v3.6 — Agent Capabilities II

Goal: the rest of the agent toolset, riding v3.5's faster routing.

- [ ] Screenshot tool (capture + OCR via a local model)
- [ ] Window control (focus, minimize, list windows)
- [ ] Browser automation via Playwright (search, open, scrape)
- [ ] Multi-step tool plans (e.g. "open VS Code and start the dev server")

---

## v3.7 — Smarter Memory

Goal: memory that gets better over time (groundwork already laid — saves now
extend the embedding cache incrementally instead of re-encoding all).

- [ ] Hybrid retrieval: BM25 (fastembed has it) + dense, then re-rank
- [ ] Auto-summarize long conversation chains into long-term memory
- [ ] Per-topic memory partitioning
- [ ] Memory decay / pruning policy
- [ ] Document re-index watcher (auto-rebuild when `data/documents/` changes)
- [ ] Source citations in LLM answers (which chunk → which file)

---

## v4.0 — Iron Man Interface (data UIs)

Goal: the data-management UI, plus the one missing interaction.

> **Partly shipped in v3.2.0.** The HUD chose **pywebview + vanilla JS over a
> local WebSocket** instead of the Tauri/React/FastAPI stack originally sketched.
> The orb, live waveform, and dual subtitles are done. What remains is below.

- [x] Animated wake-word orb · live dual subtitles · always-on-top overlay + type input
- [ ] **Echo cancellation** — interrupt by *speaking* mid-reply (today the mic hears
      Jarvis's own TTS; Stop/Esc/typing are the only interrupts). The last big UX gap.
- [ ] Memory dashboard (search + edit memories)
- [ ] Document drop zone (PDFs → auto-index)
- [ ] Reminder list + edit
- [ ] Conversation history panel
- [ ] Command palette

---

## v5.0 — Distribution

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
