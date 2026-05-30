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
