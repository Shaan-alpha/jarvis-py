## v3.5.2 — HUD close button & app logo (2026-06-19)

- **HUD close + minimize controls.** The frameless HUD now has a top title bar
  with **×** and **–** buttons. Closing sends a `shutdown` command over the
  WebSocket — the backend stops TTS playback + queue and reminders, then
  `os._exit(0)` — and the HUD destroys its own window via a pywebview `js_api`,
  so **both processes exit and the mic is released** (no orphan left running).
  (`hud/web/*`, `hud/window.py`, `app.py`)
- **App logo.** An arc-reactor "J" mark matching the HUD theme: `hud/web/logo.svg`
  (favicon + title-bar brand mark) and a Pillow-drawn `assets/jarvis.png` +
  multi-size `assets/jarvis.ico` (regen with `assets/make_logo.py`), wired into
  `jarvis.spec` (`icon=`) for the built `.exe`/window.
- **Orb glass refinement.** The fluid orb is now a *contained glass sphere*: a
  clipping `.orb-body` wrapper keeps the screen-blended colour layers inside a
  crisp circle over a deep base (vivid flow instead of washing out to white),
  with a glassy `.orb-rim` (bright top edge, soft dark bottom, faint accent
  ring) and a smaller, repositioned specular glint. (`hud/web/index.html`,
  `hud/web/style.css`)
- **UI cleanup.** Slim brand title bar; removed a dead `.top` selector from the
  reduced-motion rule; window height nudged to fit the new bar.
- Tests: +2 (shutdown WS dispatch + the shutdown handler stops services then
  exits). 269 pass; lint clean. Verified live: × shut down backend + HUD, no
  orphan processes.

## v3.5.1 — Audio capture fixes (2026-06-18)

Fixes the voice pipeline on Windows multi-device setups, found by running the app
on a laptop whose OS-default mic was Bluetooth earbuds.

- **Fix — wake word never fired ("can't hear me").** The wake-word listener
  force-opened the mic at 16kHz; on a 44.1/48kHz device via PyAudio's MME host
  that delivers degraded audio openWakeWord scores ~0. It now captures at the
  device's **native rate via WASAPI** and resamples to 16kHz in software
  (`scipy.signal.resample_poly`), downmixing multi-channel input.
  (`core/speech/openwakeword_listener.py`)
- **Fix — bot inaudible after one sentence ("can't hear bot"); regresses v3.5.0.**
  v3.5.0's persistent per-thread `pyttsx3` engine (PR #12) only spoke its first
  utterance — a reused SAPI engine is silent on subsequent `runAndWait()` calls,
  so the TTS-queue worker went mute after one sentence. Reverted to a **fresh
  engine per utterance**. (`core/speech/engine.py`)
- **Purpose-aware, Bluetooth-avoiding mic selection.** Wake word and STT now use
  the same physical mic via the host API each needs — **WASAPI** for the wake word
  (clean audio) and **MME/DirectSound** for STT (intelligible mono that Google
  transcribes) — via separate `WAKE_DEVICE_INDEX` / `INPUT_DEVICE_INDEX`.
  Bluetooth/headset HFP mics are de-prioritised (unusable for detection).
  (`core/setup/checks.py`, `config/settings.py`, `app.py`)
- **Wake threshold 0.6 → 0.3.** Clean WASAPI capture keeps ambient near 0, but
  real "hey jarvis" utterances vary ~0.47–0.97 by distance/articulation; 0.3 with
  the existing 2-frame debounce fires reliably without spurious wakes.
- **Dependency:** add `scipy` (mic-audio resampling).
- Tests: new `tests/test_wake_resample.py`; selection + recovery tests updated.
  267 pass; lint clean. Verified live end-to-end: wake → STT → tool → spoken answer.

## v3.5.0 — Responsiveness & Efficiency (2026-06-18)
- **Latency instrumentation** (`core/utils/metrics.py`): a per-turn `Timeline`
  records stage marks and emits a compact summary (`route`/`first_token`/
  `first_audio`/`total`) to the log + a HUD `metrics` event. Wired into
  `process_query` (turn boundaries + `routed`) and the Ollama stream
  (`first_token` / `first_audio`). Behaviour-neutral; establishes the latency
  baseline the rest of v3.5 is measured against. STT/wake stage marks + a HUD
  readout are the next follow-up.
- **Faster tool selection**: `decide_tool` now caps the Ollama call
  (`num_predict=80`, `temperature=0`) so the tiny selection JSON returns quickly
  and deterministically instead of an unbounded completion blocking before
  `ask_llm`.
- **TTS engine reuse** (`core/speech/engine.py`): each speaking thread keeps a
  persistent `pyttsx3` engine in thread-local storage and reuses it across
  streamed sentences instead of re-initialising one per sentence (the hot path).
  The failure path drops the (possibly wedged) engine so the next call re-inits,
  preserving the old per-call crash recovery. (PR #12)
- **Warm-start** (`core/warmup.py`): on launch, a daemon thread preloads the LLM
  (priming ping) and the embedding model off the critical path so the user's
  first real query isn't a cold start. Each step is best-effort — a failure is
  logged and the component just lazy-loads on demand. Vosk and the wake-word
  model are intentionally not warmed. (PR #14)
- **Model bake-off** (`model_bakeoff.py`): a CI-safe benchmark script that scores
  candidate local Ollama models on tool-selection accuracy and chat latency
  (TTFT + total), skipping models that aren't pulled. Pure-logic helpers are
  unit-tested; the I/O runs only against a live Ollama. (PR #13)
- **Fix — silent Ollama error status**: `ask_llm` now checks the HTTP status
  before streaming. Previously a non-200 (commonly a 500 when the model needs
  more memory than is free) streamed a body with no tokens, so the user heard
  nothing; it now logs the error and speaks a concise message (memory-specific
  when the model is out of RAM). +1 test.

## v3.4.0 — Agent Capabilities & Hardening

### Audit hardening (2026-06-17)
Deep-audit follow-up (see `docs/AUDIT-2026-06-17.md`). 26 new tests; CI green.
- **Security**: the HUD WebSocket now rejects remote `http(s)` origins, so a web
  page you visit can't drive `ws://127.0.0.1` (open/close apps, write files).
- **Crash-safe persistence**: profile/tasks/memory writes go through a new
  `core/utils/jsonio.py` (temp file + `os.replace`); reads tolerate a missing or
  corrupt file. The semantic- and document-memory caches are now lock-guarded.
- **Memory perf**: saving a turn extends the embedding cache incrementally
  instead of re-encoding every memory (was O(n²) over a session).
- **Content fidelity**: typed queries keep their original case/punctuation for
  `write_clipboard` / `write_file` / web-search terms (`raw_query` threading).
- **NLU**: reminders understand hours/seconds, short forms, "a/an/half an", and
  the reversed word order; profile capture stops at clause boundaries and is
  length-capped; the LLM action-gate no longer fires on long chit-chat.
- **TTS**: `speak()` routes through the locked `speak_sync` so it can't run a
  second engine concurrently with the TTS-queue worker.
- **Robustness/cleanup**: `read_pdf` tolerates `None` page text; `build_index`
  creates the documents dir; registry gains `float`/`bool` arg coercers; dead
  `wait_until_done()` removed; `_start_hud`/`resolve_keyword_tool` flattened
  under the complexity gate.

### Agent Capabilities (Layer 1 + Layer 2)
- **File-system tools (Layer 2)**: `list_files` / `read_file` / `write_file` /
  `search_files` in a sandboxed `user_data_dir()/workspace` root (path-traversal
  guard); `list_files` has a keyword fast-path, the rest are LLM-only. (PR #9)
- **Clipboard tools (Layer 2)**: two registry `@tool`s — `read_clipboard` (returns
  the clipboard text; empty/whitespace → "The clipboard is empty.", verbatim up to
  200 chars, a length report + truncated preview beyond) and `write_clipboard(text)`
  (copies + confirms), backed by `pyperclip` (now pinned explicitly). `read_clipboard`
  has an instant keyword fast-path ("read my clipboard", "what's on my clipboard", …);
  `write_clipboard` is LLM-only, so a "copy … to clipboard" command routes through the
  agent. The first v3.4 capability tool. (PR #7)
- **Tool foundation (Layer 1)**: a tool registry + `@tool` decorator, stdlib
  argument coercion/validation, a `builtins` tool module, and a plugin loader
  (`plugins/` plus `%APPDATA%\JarvisAI\plugins`). `decide_tool` now selects from
  the registry and returns a `ToolCall`, and `execute_tool` is a generic registry
  dispatch — both wired into the voice loop. Ships an example `roll_dice` plugin
  and plugin-authoring docs. (PR #4)

## v3.3.0

### Polish & Packaging
- **Windows packaging**: `build.ps1` + `jarvis.spec` produce a one-folder
  `dist/JarvisAI/` app via PyInstaller, bundling the Vosk + wake-word models, the
  HUD UI, and the native libraries for Vosk/openWakeWord/FAISS/fastembed
  (`collect_all`). All paths resolve via `core/paths.py` (`resource_dir()` →
  PyInstaller's `_internal/` when frozen for bundled assets; `user_data_dir()` →
  `%APPDATA%\JarvisAI`), so a packaged app reads/writes in the right places. Dev
  (`python app.py`) is unchanged. Run `Jarvis.exe --check-paths` to verify a build.
- **First-run setup wizard** (HUD): checks Ollama, the model, the microphone, and
  the WebView2 runtime; offers a guided `ollama pull`; captures your name. The HUD
  auto-launches on first run regardless of `--hud`; later launches respect the flag.
- **Crash-recovery / graceful degradation**: friendly message when Ollama is
  unreachable; clean exit with guidance when no microphone is present; online-only
  fallback when the Vosk model can't load; TTS engine re-initialises after a
  failure instead of going silent. Microphone auto-detect picks a working device.

### Frozen build (found by running the packaged .exe)
- `resource_dir()` resolves bundled assets via `sys._MEIPASS` (PyInstaller 6
  one-folder builds put data under `_internal/`, not beside the exe).
- `jarvis.spec` collects the **native libraries** for Vosk/openWakeWord/FAISS/
  fastembed (`collect_all`) — a bare hidden-import doesn't, so `import vosk`
  crashed in the frozen app.
- The HUD runs on the **main thread** when frozen (pywebview requires it); the
  voice loop moves to a background thread. Closing the HUD window quits the app.

### Voice quality & interaction
- **Interrupt controls**: a **Stop** button (and `Esc`) in the HUD instantly cut
  Jarvis off; typing a new question also interrupts (stops the current utterance,
  clears the queue), and a newer query cancels an in-flight LLM stream instead of
  queueing behind it. (Interrupting by *speaking* isn't supported — the mic hears
  Jarvis's own voice — so use Stop / Esc / typing.)
- **No more context bleed / rambling**: document & memory retrieval is gated off
  short/greeting queries (e.g. "how are you" no longer pulls in unrelated indexed
  content), and the similarity thresholds were raised so only clearly-relevant
  matches are used. Fixes a class of hallucination where a small model would
  confabulate around a weakly-matched chunk.
- **Full-phrase capture**: raised the speech pause threshold so multi-word
  utterances ("how are you") aren't cut off after the first word, plus a
  `MAX_ENERGY_THRESHOLD` cap so quiet speech is still heard in noisier rooms.
- **No more spurious wake-ups**: `WAKE_THRESHOLD` 0.4 → 0.6 and a 2-frame debounce
  (`WAKE_CONSECUTIVE`) so ambient noise no longer wakes Jarvis on its own.
- **Startup greeting** is spoken synchronously after the TTS queue starts, so it
  is no longer truncated.

### Desktop HUD redesign
- The orb is now a **fluid, glassmorphism "Siri/ChatGPT" blob** (pure CSS — no
  WebGL/Three.js dependency): flowing multi-colour gradient layers that morph and
  blend, audio-reactive (it doubles as the mic visualizer) and state-reactive, over
  an ambient aurora background with frosted-glass cards. The empty caption box is
  hidden until there's a transcript/reply. Themed cyan/gold/frost by time of day.

## v3.2.0

### Desktop HUD (headline feature)
- **`python app.py --hud`** launches an optional always-on-top desktop HUD panel: an animated state orb (idle / listening / thinking / speaking), a live mic waveform, streaming captions for both you and Jarvis, a type-to-Jarvis text input, and a live status row (CPU / battery / model / online). The theme auto-switches by time of day — cyan (day), gold (evening), frosted (night) — with a manual override.
- Built with **pywebview + vanilla HTML/CSS/JS**, connected to the Python core over a local **WebSocket** (`core/hud/` + `hud/`). The voice core is unchanged and fully functional without the flag — every HUD event is a no-op when `--hud` is off. Free and fully local; no new paid services.

### Internal / quality
- Repo audit hardening: real unit-test suite (1 → 43 tests), `pyproject.toml` pytest config, pinned dev tooling, lazy-loaded embedder (faster startup + CI-importable core), cross-platform TTS init, accurate docs, lint hygiene, and removal of dead code.

## v3.1.5

### Automated Testing & CI
- **Unit Test Suite**: Added `tests/test_imports.py` and configured `PYTHONPATH` in CI workflow to ensure robust automated pytest collection and verification.

## v3.1.4

### Bug Fixes
- **Code Quality**: Removed unused global variable declaration in `tts_queue.py` to ensure pristine compliance with automated `flake8` linter checks in CI pipeline.

## v3.1.3

### Bug Fixes
- **Continuous Integration**: Installed `portaudio19-dev` and `libasound2-dev` system packages in Ubuntu runner to support successful `PyAudio` wheel builds in automated CI pipelines.

## v3.1.2

### CI & Automated Release Management
- **Continuous Integration**: Added `.github/workflows/ci.yml` to automatically verify Python syntax and run pytest on all pull requests and pushes to `main`.
- **Release Drafter Bot**: Deployed Release Drafter workflow (`release-drafter.yml`) to automatically compile semantic release notes based on PR labels (`bug`, `enhancement`, `ci`).

## v3.1.1

### Community & Repository Virality
- **Sponsor & Funding Integration**: Added `.github/FUNDING.yml` enabling the Sponsor button to support continuous local AI assistant research.
- **Community Health Files**: Added interactive YAML issue templates (`bug_report.yml`, `feature_request.yml`) and a professional `PULL_REQUEST_TEMPLATE.md` to streamline OSS contributions.

## v3.1.0

### Features
- **Wake-word barge-in**: say "hey jarvis" while Jarvis is speaking
  to cut the response and immediately listen for a new command.
  Internally: `wait_until_done_or_barge_in()` spawns a cancellable
  background wake-word listener while the TTS queue drains.

### Fixes
- **TTS no longer collides mid-sentence.** Streamed sentences used to
  spawn overlapping pyttsx3 threads producing "run loop already
  started" errors. The TTS worker now calls `engine.speak_sync()` so
  each sentence finishes fully before the next is dequeued.
- **Wake-word residual buffer.** A previous session's "hey jarvis" (or
  TTS bleed) used to re-trigger detection within 200 ms of returning to
  sleep mode. Now the listener calls `model.reset()` plus drains 12
  audio chunks on every call.
- **STT capture window widened.** Phrases were truncated mid-sentence
  (`"explain transformers in two lines"` → `"transformers in two
  lines"`). `pause_threshold` 1.2→0.8, `phrase_time_limit` 5→12.
- **Tool agent over-triggering fixed.** Casual queries like
  "transformers in two lines" used to be routed to `open_youtube`.
  Now there is an action-verb gate before the LLM call, the prompt is
  much stricter with explicit refusal examples, JSON extraction is
  tolerant of stray prose, and tool names are case-normalised.
- **Doc-RAG was leaking the user's résumé into every prompt.** Added
  `DOCUMENT_SIMILARITY_THRESHOLD` (default 0.45) — chunks below score
  are dropped. LLM prompt also tells the model to ignore profile +
  documents unless the question is clearly about them.
- **`WAKE_THRESHOLD` 0.5 → 0.4** for a bit of margin (testing peak
  was 0.97).
- **`system status`, `system info`, `cpu usage`, `battery
  status/level/percentage`** now map to `handle_system_status` (was
  only `system condition` / `condition of the system`).

### Privacy / Repository hygiene
- `data/profile/user_profile.json` and the bundled Vosk model
  (`models/vosk/vosk-model-small-en-us-0.15/`, ~70 MB) are no longer
  tracked — they were leaking on `origin/main`.
- `.gitignore` now uses allowlist patterns so each runtime folder
  keeps a placeholder `README.md` explaining what goes in it, but no
  user data or models.

### Tooling
- New `debug_wake.py` script for diagnosing wake-word detection
  (lists input devices, shows live RMS + confidence per chunk).

## v3.0.0
- Swapped `sentence-transformers` (~2 GB with torch/transformers) for
  `fastembed` (ONNX-only, ~90 MB model). venv site-packages: 2050 MB
  → 552 MB.
- Embedding model cached at `models/embeddings/`; fastembed already
  returns L2-normalized vectors.
- FAISS index switched from `IndexFlatL2` → `IndexFlatIP` for true
  cosine similarity on normalized vectors. **Breaking:** existing
  vector indexes must be rebuilt — run `python build_memory.py`.
- Wake-word listener now lazy-loads on first call and prefers a
  project-local `models/wake/hey_jarvis_v0.1.onnx` (settings:
  `WAKE_WORD`, `WAKE_MODEL_PATH`). Package + auto-download as
  fallbacks.
- `system_status` now speaks one tight sentence (CPU %, battery %,
  charging state) instead of 3-5 separate utterances.
- README, CHANGELOG, requirements updated for the new stack.

## v2.4.0
- Removed dead Keras intent-classifier pipeline (chat_model.h5, train.py,
  tokenizer, label_encoder, model_test)
- Removed orphan `core/memory/memory.json` seed file and outdated
  `docs/README.md`
- Dropped scikit-learn dep — semantic-memory cosine is now numpy
- Vosk now loads from local `models/vosk/...` (auto-download fallback)
- Connectivity check constants moved into settings
  (ONLINE_CHECK_HOST/PORT/TIMEOUT, ONLINE_CACHE_TTL)
- Routing reordered: keyword router (fast) → LLM tool agent (slow) →
  LLM chat fallback. Previously every query hit the LLM tool agent
  first even for trivial commands.
- Vosk model pre-warmed in a background thread at app startup so the
  first offline transcription does not pay the model-load cost
- Reminders rewritten with threading.Timer (one-shot, second-accurate);
  dropped the `schedule` lib and its minute-rounding restore bug
- requirements.txt trimmed and grouped; requirements-dev.txt slimmed
- Stale requirements-lock.txt removed
- .gitignore now excludes runtime caches (vector.index, chunks.pkl,
  semantic_memory.json, tasks.json)
- README updated to reflect dual STT + lean stack

## v2.3.0
- Hybrid online/offline STT with auto-fallback (Google ↔ Vosk)
- New connectivity check `is_online()` in speech/engine
- Fixed browser handler to URL-encode and open a real Google search

## v2.2.0
- Real wake-word detection via openWakeWord (`hey_jarvis`)
- Replaces the broken stub that loaded every bundled pretrained model
- WAKE_THRESHOLD pulled from settings; clean PyAudio teardown

## v2.1.0
- Removed duplicate `User said` / `Jarvis:` console prints
- Centralized embedder, cached document index + memory embeddings
- Unified tool agent/executor schema via `tool_registry` (executor was
  importing a non-existent `core.actions.system_actions` module)
- Greeting reads name from user profile
- Populated `data/profile/user_profile.json`
