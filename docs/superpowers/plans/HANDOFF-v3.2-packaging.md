# HANDOFF — v3.2 Polish & Packaging (in progress)

> Cold-agent catch-up for resuming the v3.2 packaging milestone. Read this, then
> the plan, then continue. Written 2026-05-30 at a clean pause point.

## TL;DR

- **Branch:** `feature/v3.2-packaging` (off `main`). Working tree **clean**, all work committed, **not pushed**.
- **Baseline:** `96 passed`, build-breaking flake8 `0`, quality flake8 `8` (all pre-existing). (`.\venv\Scripts\python.exe -m pytest` / `... -m flake8 . --select=E9,F63,F7,F82,F401 --count` — a `.flake8` now sets the excludes incl. `build,dist`.)
- **Build is verified working** (PyInstaller one-folder). `.\build.ps1` → `dist\JarvisAI\`; `Jarvis.exe --check-paths` reports all assets `[OK]` and the HUD opens. Three frozen-only bugs + voice-quality issues were found by running the exe and fixed — see "Post-Phase-6" below. **Still owed: the USER's full interactive smoke-test sign-off (Task 26) before the PR/merge/tag.**
- **Plan:** [`docs/superpowers/plans/2026-05-30-v3.2-packaging.md`](2026-05-30-v3.2-packaging.md) — 28 tasks, 6 phases.
- **Spec:** [`docs/superpowers/specs/2026-05-30-v3.2-packaging-design.md`](../specs/2026-05-30-v3.2-packaging-design.md).
- **Execution method:** superpowers **subagent-driven-development** — fresh implementer subagent per phase, then two-stage review (spec compliance → code quality). Use the venv python (`.\venv\Scripts\python.exe`) for all subagent commands; CI is Ubuntu so keep tests CI-safe (no real mic/display/Ollama/network — inject deps).

## Progress

| Phase | Tasks | Status |
|---|---|---|
| 1 — paths resolver | 1–3 | ✅ done, both reviews passed |
| 2 — path migration | 4–8 | ✅ done, both reviews passed |
| 3 — setup checks | 9–14 | ✅ done, both reviews passed |
| 4 — recovery + mic | 15–18 | ✅ done, both reviews passed (caught a CRITICAL import-time-copy bug, fixed) |
| 5 — wizard/launch | 19–22 | ✅ **done — 3 owed fixes applied (`672ce98`), code-quality reviewer re-run, follow-ups applied (`fb4018f`); reviewer verdict Ready-to-merge** |
| 6 — build/docs | 23–28 | ✅ **agent tasks done (23–25 `2f75863 90143a3 309f80d`, 27 `51091d4`, 28 `d914be6`). RESUME HERE: Task 26 — the MANUAL Windows build + smoke test — is the only thing left and is USER-ONLY.** |

## Phase 5 resolution (history)

The 3 owed code-quality fixes were applied in `672ce98` and the reviewer was re-run:
- **Issue 1** — no-mic exit now uses `speak_sync(...)` (synchronous; banner finishes before exit); import added.
- **Issue 2** — `_on_pull_model` runs `pull_model` in a daemon `threading.Thread`; `pull_done` emitted in a `try/finally` (follow-up `fb4018f`) so the wizard log always gets a "done" transition even on failure.
- **Issue 3** — wizard now carried in the WS `ready` handshake via `ws_server.set_wizard_mode(bool)` + `_wizard_mode` flag; `app.js` opens the wizard on `ready.wizard`. The old `events.emit("show_wizard")` and the now-dead `case "show_wizard"` in `app.js` were removed.
- Reviewer follow-ups (`fb4018f`): `try/finally` on the pull + dead-JS removal. Verdict: **Ready to merge.** Baseline now **91 passed, build-breaking lint 0**, tree clean.

The minor non-blocking notes (`_dispatch_command` if-chain → dict; `wizard.js` hard-codes `"phi3"`) were left as-is — optional, skip unless trivial.

## Phase 6 — agent tasks done; only the MANUAL Task 26 remains

Done (committed on the branch): Task 23 `pyinstaller>=6.0` (`2f75863`), Task 24
`jarvis.spec` + gitignore build/dist (`90143a3`), Task 25 `build.ps1` (`309f80d`),
Task 27 README build section + CHANGELOG v3.3.0 + `pyproject.toml` bump to 3.3.0
(`51091d4`), Task 28 CLAUDE.md §2/§5/§6 + PLAN.md (`d914be6`). Suite **91 passed**,
build-breaking lint **0**, quality lint **10** (all pre-existing), tree clean.

**RESUME HERE — Task 26 (MANUAL, USER-ONLY):** the Windows build + smoke test.
The agent CANNOT run it (needs a real display, mic, Ollama, and the gitignored
models under `models/`). The checklist (plan Task 26): ensure models present →
`.\build.ps1` → first-run HUD opens/checks/pull/name/Start + `%APPDATA%\JarvisAI\
data\profile\user_profile.json` written → second run voice-only, `--hud` shows HUD,
"hey jarvis" responds → degradation: Ollama-down message + alive, no-mic message +
clean exit. Record outcomes for the PR body.

## Post-Phase-6 — fixes found by building & voice-testing the exe (not in the plan)

Running the real `Jarvis.exe` surfaced bugs that unit tests / `python app.py`
could not. All fixed, committed, suite green, build re-verified. See the memory
note `pyinstaller-freeze-gotchas` for detail.

- **Frozen path resolver** (`cbd9de0`): `resource_dir()` → `sys._MEIPASS` (PyInstaller 6 puts datas in `_internal/`, not beside the exe). `.flake8` added (excludes `build,dist`). New `app.py --check-paths` diagnostic.
- **Native libs not bundled** (`cbd9de0`): `jarvis.spec` uses `collect_all()` for vosk/openwakeword/faiss/fastembed (vosk loads `libvosk.dll` at import; a bare hiddenimport doesn't collect native DLLs/model data).
- **Frozen HUD crashed** (`ca8c9e6`): pywebview must own the main thread. Voice loop extracted to `_voice_loop()` on a daemon thread; `window.launch()` runs on the main thread when frozen (close window = quit). Removed `window.start_in_thread()`.
- **Voice quality** (`dba7db3`, `faa51a8`, `7547d90`): RAG/memory retrieval gated off chitchat + thresholds raised (0.45→0.6 / 0.55) to stop hallucination from weak résumé matches; STT `pause_threshold` 0.8→1.2 (full-phrase capture); startup greeting via `speak_sync`; **typed-query barge-in** (stop+clear + an `ask_llm` generation token that cancels superseded streams); `_stream_response` extracted from `ask_llm` (complexity).
- **Model:** staying on `phi3` (user's call). `llama3:latest` is already pulled if a quality bump is wanted later — just change `MODEL_NAME` in `config/settings.py`.

## Final wrap (after Phase 6)
- Full verification (plan's "Final verification" section): suite green, lint 0, dev `python app.py [--hud]` unchanged.
- Then use superpowers **finishing-a-development-branch**: open a PR to `main`, label `feature`, paste the user's Task 26 smoke-test results in the PR body. Do NOT merge without the manual smoke test.
- User standing rule: **always git-tag + cut a GitHub Release** on ship (don't stop at merge) — tag `v3.3.0`.

## Conventions (carry forward)
- Commit footer on EVERY commit: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Commit/push only when the user asks. Branch off `main`, never commit to `main`.
- House style: `core/**`, `app.py`, `config/` use a blank line between most statements + grouped imports; tests use the tighter conventional style.
- `core/paths.py` is stdlib-only (no project imports) — never add a project import there (circular-import risk via logger).
- Mic index gotcha (already fixed in Phase 4, don't regress): read `config.settings.INPUT_DEVICE_INDEX` LIVE via `import config.settings as settings` — never `from config.settings import INPUT_DEVICE_INDEX` (import-time copy makes auto-detect inert).

## Useful state
- New modules this milestone: `core/paths.py`, `core/setup/{__init__,checks,first_run}.py`.
- New tests: `test_paths`, `test_settings_paths`, `test_data_paths`, `test_setup_checks`, `test_mic_select`, `test_first_run`, `test_recovery`, `test_hud_window`, `test_hud_wizard_dispatch`, `test_app_firstrun`.
- Wizard UI: `hud/web/wizard.js` (a `window.Wizard` IIFE — app.js is plain IIFE, NOT ES modules), plus wizard section in `index.html`/`style.css` and event routing in `app.js`.
