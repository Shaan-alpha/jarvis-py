# HANDOFF — v3.2 Polish & Packaging (in progress)

> Cold-agent catch-up for resuming the v3.2 packaging milestone. Read this, then
> the plan, then continue. Written 2026-05-30 at a clean pause point.

## TL;DR

- **Branch:** `feature/v3.2-packaging` (off `main`). Working tree **clean**, all work committed, **not pushed**.
- **Baseline:** `89 passed`, build-breaking flake8 `0`. (`.\venv\Scripts\python.exe -m pytest` / `... -m flake8 . --select=E9,F63,F7,F82,F401 --exclude=venv,__pycache__ --count`)
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
| 5 — wizard/launch | 19–22 | ⚠️ **implemented + spec-review PASSED, but code-quality review returned CHANGES REQUESTED — 3 fixes still owed (see below)** |
| 6 — build/docs | 23–28 | ⛔ not started |

## ⚠️ RESUME HERE — Phase 5 has 3 unaddressed code-quality issues

Phase 5 code is committed (`f9d544a ec54e53 23f7316 bd59b90`) and passed spec compliance, but the **code-quality review returned CHANGES REQUESTED**. These fixes were NOT yet applied. Apply them first, then re-run the code-quality reviewer before moving to Phase 6.

**Issue 1 (Important — real bug): "no microphone" exit message gets cut off.**
`app.py` `main()` mic gate does `speak(...)` then `stop_tts_queue()` then `return`. `speak()` spawns a daemon thread and returns immediately, so the process exits before the message plays. **Fix:** use `speak_sync(...)` instead of `speak(...)` for this one-shot exit banner (it's the correct synchronous semantic). `speak_sync` already exists in `core/speech/engine.py`. NOTE: `app.py` currently imports `speak` (not `speak_sync`) — add the import.

**Issue 2 (Important — real bug): `_on_pull_model` blocks the WS asyncio loop, so the pull-progress log never streams live.**
In `app.py` `_start_hud`, `_on_pull_model` calls the BLOCKING `pull_model(...)` directly on the WS thread. While `ollama pull` runs (minutes), the asyncio event loop and the `_broadcaster` (in `core/hud/ws_server.py`) are blocked, so the `pull_progress` events queued in the event bus are NOT broadcast until the pull finishes — the live log dumps all at once at the end. **Fix:** run `pull_model` in a `threading.Thread`, and emit `pull_done` when the thread finishes (e.g. the thread target calls pull_model then `events.emit("pull_done")`). Do NOT block the handler. Add a small test if practical (the handler should return promptly).

**Issue 3 (Important — real correctness, low repro): `show_wizard` races HUD connect.**
In `_start_hud`, `events.emit("show_wizard")` fires before the HUD client has connected to the WS. The event bus broadcasts only to connected clients (not a persistent mailbox), so on a slow start the wizard may never show. **Fix (cleanest):** carry a `wizard` flag in the `ready` handshake that `ws_server._handle_client` already sends (it currently sends `type:"ready"` + state + theme — add `"wizard": <bool>`), and have `hud/web/app.js` call `Wizard.showWizard(send)` when it receives `ready` with `wizard: true`. This needs a module-level flag in `ws_server` set by `_start_hud` (e.g. `ws_server.set_wizard_mode(True)`), since the handshake is built in `_handle_client`. Then the `events.emit("show_wizard")` in `_start_hud` can stay as a belt-and-suspenders OR be removed in favor of the handshake. Coordinate the JS: `app.js` already routes `show_wizard`; just also trigger on `ready.wizard`.

**Minor notes from the review (optional, non-blocking):** `_dispatch_command` if-chain could become a dict (maintainability); `test_select_mic_sets_index` could also assert `is True`; `wizard.js` hard-codes `"phi3"` (could read from a `show_wizard`/`ready` payload carrying `config.settings.MODEL_NAME`); pywebview-on-non-main-thread is macOS-only risk (Windows is fine — documented). Skip unless trivial.

After applying Issues 1–3: run full suite + lint, then dispatch the **code-quality reviewer** on the fix commit. Only when it returns ✅ APPROVED is Phase 5 complete.

## Then: Phase 6 (Tasks 23–28) — not started

Follow the plan verbatim. Key points:
- **Task 23:** add `pyinstaller>=6.0` to `requirements-dev.txt`.
- **Task 24:** create `jarvis.spec` (one-folder; `datas` bundles `models/` + `hud/web`; excludes tkinter/matplotlib/PyQt5/PySide6; hiddenimports webview/vosk/openwakeword/faiss/fastembed).
- **Task 25:** create `build.ps1`.
- **Task 26 — MANUAL, USER-ONLY:** the Windows build + smoke test. The agent CANNOT run this (needs a real display, mic, Ollama, and the gitignored models present under `models/`). **Stop and hand this to the user** with the smoke-test checklist from the plan; do not attempt to build/run the HUD yourself.
- **Task 27:** README build section + CHANGELOG entry + version bump. **Ships as `v3.3.0`** (the HUD already took v3.2.0) — the plan's Task 27 Step 3 explains this. Don't accidentally set 3.2.0.
- **Task 28:** update `CLAUDE.md` (§2 state, §5 add `core/paths.py` + `core/setup/`, §6 gotcha: never hardcode CWD-relative paths — use `core.paths`) and `PLAN.md` (mark v3.2 milestone done + add v3.3.0 row).

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
