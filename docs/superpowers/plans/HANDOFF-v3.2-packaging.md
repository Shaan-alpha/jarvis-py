# HANDOFF — v3.2 Polish & Packaging (in progress)

> Cold-agent catch-up for resuming the v3.2 packaging milestone. Read this, then
> the plan, then continue. Written 2026-05-30 at a clean pause point.

## TL;DR

- **Branch:** `feature/v3.2-packaging` (off `main`). Working tree **clean**, all work committed, **not pushed**.
- **Baseline:** `91 passed`, build-breaking flake8 `0`. (`.\venv\Scripts\python.exe -m pytest` / `... -m flake8 . --select=E9,F63,F7,F82,F401 --exclude=venv,__pycache__ --count`)
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
| 6 — build/docs | 23–28 | ⛔ **RESUME HERE — not started** |

## Phase 5 resolution (history)

The 3 owed code-quality fixes were applied in `672ce98` and the reviewer was re-run:
- **Issue 1** — no-mic exit now uses `speak_sync(...)` (synchronous; banner finishes before exit); import added.
- **Issue 2** — `_on_pull_model` runs `pull_model` in a daemon `threading.Thread`; `pull_done` emitted in a `try/finally` (follow-up `fb4018f`) so the wizard log always gets a "done" transition even on failure.
- **Issue 3** — wizard now carried in the WS `ready` handshake via `ws_server.set_wizard_mode(bool)` + `_wizard_mode` flag; `app.js` opens the wizard on `ready.wizard`. The old `events.emit("show_wizard")` and the now-dead `case "show_wizard"` in `app.js` were removed.
- Reviewer follow-ups (`fb4018f`): `try/finally` on the pull + dead-JS removal. Verdict: **Ready to merge.** Baseline now **91 passed, build-breaking lint 0**, tree clean.

The minor non-blocking notes (`_dispatch_command` if-chain → dict; `wizard.js` hard-codes `"phi3"`) were left as-is — optional, skip unless trivial.

## RESUME HERE: Phase 6 (Tasks 23–28) — not started

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
