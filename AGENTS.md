# AGENTS.md

This project's agent onboarding, current state, active task, and rules live in a
single canonical file:

➡️ **[CLAUDE.md](CLAUDE.md)**

Read it first. It applies to all AI agents working in this repo (Claude Code,
Codex, Gemini CLI, Copilot, etc.), not just Claude.

**TL;DR:**
- Local-first Python voice assistant, **Windows-first**, **free/local/zero-money only**.
- Active work is on branch `feature/jarvis-hud`: implementing the **desktop HUD**
  (pywebview + vanilla web + local WebSocket). Source of truth:
  - Spec: `docs/superpowers/specs/2026-05-30-jarvis-hud-design.md`
  - Plan: `docs/superpowers/plans/2026-05-30-jarvis-hud.md`
- Run: `python app.py` · Test: `python -m pytest` · Branch off `main`, never commit to it directly.
- Use Context7 MCP for library/framework docs.
