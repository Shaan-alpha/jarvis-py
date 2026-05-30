# CLAUDE.md — Agent onboarding for jarvis-py

> Read this first. It is the catch-up file for any fresh ("cold") agent. It
> captures what the project is, where we are right now, the active task, and the
> rules you must follow. Keep it updated when state changes.

---

## 1. What this project is

**jarvis-py** is a local-first AI **voice assistant** (Python, Windows-first). It
does wake-word detection ("hey jarvis"), online/offline speech-to-text, local LLM
inference via Ollama, semantic + document (PDF) memory, a keyword/LLM tool-agent
for OS actions, reminders, and interruptible streaming TTS with wake-word
barge-in.

- **Entry point:** [`app.py`](app.py) — the main voice loop.
- **Architecture reference:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (module map + request lifecycle). Read it before changing core flow.
- **Roadmap:** [`PLAN.md`](PLAN.md).
- **Repo:** `Shaan-alpha/jarvis-py`. Default branch: `main`. Latest release: `v3.2.0`.

Tech: Ollama (phi3), fastembed (ONNX embeddings), FAISS, Vosk (offline STT),
Google STT (online, free endpoint), openWakeWord (ONNX), pyttsx3 (TTS), PyAudio,
psutil, PyAutoGUI.

---

## 2. Where we are right now (2026-05-30)

A full audit was completed, the repo was hardened, and the **Jarvis HUD shipped**
as **`v3.2.0`** (on `main`, PR #2). The **v3.3.0 "Polish & Packaging"** milestone
is now **code-complete** on branch `feature/v3.2-packaging` (off `main`, not yet
merged): Windows one-folder packaging (`build.ps1` + `jarvis.spec`), a `core/paths.py`
resolver + path migration, a HUD **first-run setup wizard**, mic auto-detect, and
crash-recovery / graceful degradation. **Pending:** the manual Windows build +
smoke test (Task 26 — USER-only; needs a real display/mic/Ollama + the gitignored
models), then PR → `main`, tag **`v3.3.0`**, cut a Release. After that there is
**no active feature task** — the next thing comes from [`PLAN.md`](PLAN.md).

**Done & released in `v3.2.0` (on `main`):**
- Audit hardening: real unit tests (1 → 43), `pyproject.toml` (pytest config),
  pinned dev tooling, cross-platform TTS init + voice-index guard,
  `docs/ARCHITECTURE.md` rewrite, README badge/platform fixes, lint hygiene.
- Dead-code removal: `social_media()`, `schedule()` (fake placeholder timetable),
  `warm_up()` — all had no call sites.
- Lazy-init embedder so `core`/`app` import cheaply (no model download in CI).
- **Headline feature — the Jarvis HUD — is implemented and shipped.**

**The shipped HUD (design docs kept for reference, not as a TODO):**
- Spec: [`docs/superpowers/specs/2026-05-30-jarvis-hud-design.md`](docs/superpowers/specs/2026-05-30-jarvis-hud-design.md)
- Plan (all tasks complete): [`docs/superpowers/plans/2026-05-30-jarvis-hud.md`](docs/superpowers/plans/2026-05-30-jarvis-hud.md)

**HUD in one line:** a Tauri-style desktop panel — but built with **pywebview +
vanilla HTML/CSS/JS** (we deliberately chose pywebview over Tauri to avoid Rust+Node
toolchains) — that connects to the Python core over a **local WebSocket**. It shows
an animated orb (idle/listening/thinking/speaking), a live waveform, streaming
captions, a type-to-Jarvis input, and a status row, with a **time-adaptive theme**
(cyan day / gold evening / frosted night). Launched with `python app.py --hud`; the
core is byte-for-byte unchanged without the flag. Code lives in
[`core/hud/`](core/hud/) (event bus, WS server, stats/theme) and [`hud/`](hud/)
(pywebview window + `web/` UI).

---

## 3. How to run / test / lint

```bash
# venv lives in venv/ (Windows). Activate, then:
pip install -r requirements.txt          # runtime
pip install -r requirements-dev.txt      # + pytest, flake8

python app.py                            # run the assistant (needs Ollama: `ollama pull phi3`)
python app.py --hud                      # run with the desktop HUD (shipped in v3.2.0)

python -m pytest                         # tests (no PYTHONPATH needed; configured in pyproject.toml)
python -m flake8 . --select=E9,F63,F7,F82,F401 --exclude=venv,__pycache__ --count   # build-breaking lint (must be 0)
python -m flake8 . --exit-zero --max-complexity=10 --max-line-length=127 --exclude=venv,__pycache__   # quality warnings
```

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs flake8 + pytest on
Ubuntu/Python 3.11. **Keep CI green** — it's a public adoption signal.

---

## 4. Rules — follow these

### Hard constraints
- **Free / local / zero-money only.** No paid APIs, no cloud services, no paid
  signing/hosting. Every dependency must be free and open-source. Google STT uses
  the existing free `speech_recognition` endpoint (no key). Do not introduce
  anything that costs money or sends data to a paid third party.
- **Windows-first.** OS automation (app launch/close, system status) targets
  Windows. Cross-platform parity is roadmap, not assumed. The voice/LLM/memory
  core is portable; TTS uses `pyttsx3.init()` (native driver per OS).
- **Never commit** models, user data, `core/memory/semantic_memory.json`,
  `data/profile/*`, `logs/*`, or `.superpowers/` (the brainstorming working dir).
  `.gitignore` enforces this — keep it that way. The repo is privacy-clean; verify
  with `git ls-files` before adding bulk files.

### Library / framework docs
- **Use Context7 MCP** (`resolve-library-id` → `query-docs`) whenever you need
  docs for any library, framework, SDK, API, CLI, or cloud service — even
  well-known ones (pywebview, websockets, Ollama, FAISS, fastembed, etc.). Prefer
  it over web search and over relying on training data. (User-global rule.)

### Workflow
- **Superpowers flow for features:** brainstorm → spec (`docs/superpowers/specs/`)
  → plan (`docs/superpowers/plans/`) → execute. Don't write feature code without a
  spec + plan.
- **TDD** for Python logic: failing test → minimal code → pass → commit.
- **Tests must be CI-safe:** unit-test pure-logic modules only. Do **not** write
  tests that require a microphone, display, or trigger a model download. (This is
  why the embedder is being made lazy — see the plan's Task 1 — so `core`/`app`
  can be imported in CI without downloading the ONNX model.)

### Git
- **Branch off `main`; never commit directly to `main`.** No long-lived feature
  branch is active right now — cut a fresh one per task.
- **Commit/push only when the user asks.** Prefer small, focused commits.
- End every commit message with:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- This repo historically **bumps the version + adds a CHANGELOG entry** on release
  commits; Release Drafter labels PRs (`feature`, `bug`, `ci`, `documentation`,
  `breaking-change`). Follow that on integration commits.
- Files are CRLF (Windows). Git normalizes to LF on commit; the "LF will be
  replaced by CRLF" warnings are expected and harmless.

### Code style
- **Match the file you're editing.** Core modules (`core/**`, `app.py`,
  `config/`) use a distinctive idiom: **a blank line between most statements** and
  grouped imports. Smaller handler/automation files use a tighter conventional
  style. Don't reformat a file into a different style; mirror its neighbors.
- Line length ≤ 127; complexity target ≤ 10 (flake8). Keep modules small and
  single-purpose.

---

## 5. Key files

| Path | Purpose |
|---|---|
| [`app.py`](app.py) | Main voice loop; routing; `--hud` flag + `process_query()` |
| [`config/settings.py`](config/settings.py) | All tunables (thresholds, paths, HUD config) |
| [`core/paths.py`](core/paths.py) | Path resolver — `resource_dir()` (bundled assets) / `user_data_dir()` (writable). Stdlib-only |
| [`core/setup/`](core/setup/) | First-run checks (Ollama/model/mic/WebView2), mic auto-detect, `pull_model`, wizard helpers |
| [`core/speech/`](core/speech/) | Wake word, online/offline STT, TTS engine + queue |
| [`core/ai/ollama_engine.py`](core/ai/ollama_engine.py) | Streaming LLM client + prompt assembly |
| [`core/agent/`](core/agent/) | Tool agent, registry, executor |
| [`core/router/intent_router.py`](core/router/intent_router.py) | Fast keyword → intent handler routing |
| [`core/memory/`](core/memory/) | Embedder (lazy), semantic memory, document RAG, profile |
| [`core/tasks/`](core/tasks/) | Reminder parsing + scheduling + persistence |
| [`core/hud/`](core/hud/) | Event bus, WebSocket server, stats/theme emitter (HUD core) |
| [`hud/`](hud/) | pywebview window + `web/` vanilla UI |
| [`tests/`](tests/) | Pure-logic unit tests (CI-safe) |

---

## 6. Gotchas
- **Paths:** never hardcode CWD-relative paths — use `core.paths.resource_dir()`
  for bundled/read-only assets (models, `hud/web`) and `core.paths.user_data_dir()`
  for writable data (profile, tasks, memory, logs). When frozen (PyInstaller), CWD
  is unreliable; `resource_dir()` is the exe folder and `user_data_dir()` is
  `%APPDATA%\JarvisAI`. `core/paths.py` is **stdlib-only** — never add a project
  import there (circular-import risk via the logger).
- Importing `core.memory.*` historically instantiated the embedding model at
  import time (slow / downloads). It is now **lazy** (the embedder loads on first
  use), so `core`/`app` import cheaply in CI. Don't reintroduce eager init.
- `import pyaudio` needs PortAudio (CI installs `portaudio19-dev`).
- The visual-companion server may still be running from a brainstorming session at
  a local port; stop it with the superpowers stop-server script if needed. Its
  working files live in the gitignored `.superpowers/`.
