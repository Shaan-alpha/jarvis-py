# v3.3.0 — Polish & Packaging

> **Status (2026-06-01):** merged to `main` directly (fast-forward, no PR was
> opened). This draft is kept as the change summary; a `v3.3.0` tag + GitHub
> Release are still to be cut. A HUD overhaul also landed after this was drafted
> (fluid-blob orb, Stop/Esc + typed barge-in, wake-word + STT fixes) — see
> `CHANGELOG.md` for the complete list.

Makes jarvis-py a ship-ready app you can hand to someone: a Windows one-folder
build, a first-run setup wizard, robust path resolution, microphone auto-detect,
and graceful degradation. The voice/LLM/memory core is unchanged for dev runs
(`python app.py [--hud]` behaves exactly as before).

> Note on versioning: the HUD already shipped as **v3.2.0**, so this packaging
> milestone (named "v3.2 Polish & Packaging" in the plan) ships as **v3.3.0**.

## What's in it

**Packaging**
- `jarvis.spec` (PyInstaller one-folder) + `build.ps1` produce `dist/JarvisAI/`
  (`Jarvis.exe` + `_internal/` + bundled `models/` + `hud/web`). `pyinstaller>=6.0`
  added to `requirements-dev.txt` (build-only; not used in CI).
- New `core/paths.py` resolver: `resource_dir()` for bundled/read-only assets and
  `user_data_dir()` (→ `%APPDATA%\JarvisAI` when frozen) for writable data. All of
  logs, profile, tasks, memory, documents, and model paths now route through it, so
  a frozen app reads/writes in the right places instead of CWD-relative guesses.

**First-run setup wizard (HUD)**
- `core/setup/` adds prerequisite checks (Ollama running, model present, microphone,
  WebView2 runtime), a streamed `ollama pull`, and `is_first_run()`.
- On first run the HUD auto-launches regardless of `--hud`: it runs the checks, offers
  a guided model pull, and captures the user's name; later launches respect the flag.

**Resilience**
- Friendly spoken message when Ollama is unreachable (stays alive instead of crashing).
- Clean exit with guidance when no microphone is present.
- Online-only fallback when the Vosk model can't load.
- TTS engine re-initialises after a failure instead of going silent.
- Microphone auto-detect picks a working input device.

## Verification

- **Tests:** `96 passed` (`.\venv\Scripts\python.exe -m pytest`). All new logic is
  unit-tested CI-safe (no real mic/display/Ollama/network — deps injected).
- **Build-breaking lint:** `0` (`flake8 --select=E9,F63,F7,F82,F401`).
- **Quality lint:** `8` warnings, all pre-existing (complexity on `_start_hud`/
  `execute_tool`; E731/F841 in tests) — none introduced here.
- **PyInstaller build:** `.\build.ps1` produces `dist\JarvisAI\` successfully.
  Verified against the real frozen exe: `Jarvis.exe --check-paths` reports
  `frozen=True`, `resource_dir=...\_internal`, and all bundled asset paths `[OK]`;
  the full import chain (incl. the `vosk`/`faiss` native libs) loads, reaches
  "Listening for wake word", and the HUD window opens + connects over WS. _Three
  frozen-only bugs were found and fixed during this — see below._

### Frozen-build fixes (found by running the exe, not by tests)

- `core/paths.py`: `resource_dir()` now uses `sys._MEIPASS` when frozen. PyInstaller
  6 one-folder builds put bundled `datas` under `_internal/`, not beside the exe, so
  the old `Path(sys.executable).parent` resolved one level too high and missed the
  models + HUD UI.
- `jarvis.spec`: uses `collect_all()` for `vosk`/`openwakeword`/`faiss`/`fastembed`.
  A bare `hiddenimport` collects only Python modules; `vosk` loads `libvosk.dll` at
  import, so the native DLLs + bundled ONNX models must be collected too (otherwise
  `import vosk` crashes in the frozen exe).
- `app.py` + `hud/window.py`: the frozen HUD must run on the main thread (pywebview
  requirement). The voice loop was extracted to `_voice_loop()` and runs on a
  background daemon thread while `webview.start()` owns the main thread; closing the
  HUD window exits the app. (Dev mode is unaffected — it launches the HUD as a
  subprocess.)
- `.flake8`: excludes `build,dist` so a local build doesn't pollute the lint gate.
- New `app.py --check-paths` build diagnostic.

### Voice quality fixes (found by voice-testing the build)

- Document/memory retrieval is gated off greetings & short queries and the
  similarity thresholds were raised — stops a small model confabulating around a
  weakly-matched chunk (e.g. "how are you" pulling in an indexed résumé).
- Speech pause threshold raised so multi-word phrases aren't cut to the first word.
- Typed queries barge in (stop current speech, cancel any in-flight LLM stream).
- Startup greeting spoken synchronously so it isn't truncated.

## Manual smoke test (Task 26 — no CI build job; results recorded here)

> Run on Windows with the models present under `models/` (Vosk + wake ONNX). Replace
> each line with the outcome.

- [x] `.\build.ps1` → `dist\JarvisAI\Jarvis.exe` exists; models + HUD bundled under
      `_internal/`. `Jarvis.exe --check-paths` → all asset paths `[OK]`. _(done by Claude)_
- [ ] **First run:** move `dist\JarvisAI\` to a clean path, run `Jarvis.exe` → setup HUD
      opens automatically, runs checks, allows model pull + name entry + Start.
      `%APPDATA%\JarvisAI\data\profile\user_profile.json` written.
- [ ] **Second run:** relaunch `Jarvis.exe` (no flag) → voice-only, no HUD.
      `Jarvis.exe --hud` → HUD appears. "hey jarvis" → it responds.
- [ ] **Degradation:** stop Ollama, ask a query → says it can't reach Ollama, stays alive.
      Unplug mic + relaunch → clear "no microphone" message + clean exit.

## Docs

- `README.md`: "Build a Windows binary" section.
- `CHANGELOG.md`: v3.3.0 entry.
- `CLAUDE.md` / `PLAN.md`: state, key files, paths gotcha, roadmap renumber.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
