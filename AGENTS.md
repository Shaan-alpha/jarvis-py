# AGENTS.md

This project's agent onboarding, current state, active task, and rules live in a
single canonical file:

➡️ **[CLAUDE.md](CLAUDE.md)**

Read it first. It applies to all AI agents working in this repo (Claude Code,
Codex, Gemini CLI, Copilot, etc.), not just Claude.

**TL;DR:**
- Local-first Python voice assistant, **Windows-first**, **free/local/zero-money only**.
- Latest release: **v3.3.0** (Polish & Packaging + HUD), shipped to `main`. The
  **v3.4 Agent Capabilities** foundation (tool registry + `@tool` decorator +
  plugin loader) is merged (PR #4); next up are capability tools + orchestration.
  See [PLAN.md](PLAN.md) for the roadmap.
- Run: `python app.py` (or `--hud`) · Test: `python -m pytest` · Branch off `main`, never commit to it directly.
- Use Context7 MCP for library/framework docs.
