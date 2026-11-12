# JOBBIT — Claude Code project instructions

Read `AGENTS.md` first. It is the shared project policy for both Codex and Claude Code. Then read `README.md` and `docs/CODEX_HANDOFF.md`.

All 166 dates and their tasks are approved user data. Preserve them. Build in small independently testable steps. Do not automatically mark plans complete or send data outside the device. New AI workflows belong in opt-in integrations. `web/data/plan.json` is generated from the original spreadsheet; regenerate via `scripts/export_plan.py` rather than hand-editing the plan.

When completing a feature: run `npm run check`; include actual test evidence, limitations, and Windows-only manual tests that remain unverified.

Reusable job coaching skills are provided in `.claude/skills/` and are **instructions for the coding assistant**. They are not yet wired to run inside the JOBBIT app.
