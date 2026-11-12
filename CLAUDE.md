# JOBBIT — Claude Code project instructions

Read this file, then `README.md` and `docs/ROADMAP.md` before starting work.

## Product
Offline-first career prep desktop companion. The seed is 166 days of a real approved master plan under `web/data/plan.json`; do not regenerate, flatten or overwrite it without approval. `web/data/plan.json` is generated from the original spreadsheet; regenerate via `scripts/export_plan.py` rather than hand-editing the plan.

## Working agreement
- Claude Code is the sole developer on this project.
- Work one roadmap step at a time: **show the plan first, wait for the user's approval, then implement.**
- Each step goes on its own branch (`step-N/<topic>`) and lands through a PR; don't push feature work directly to `main`.
- Commits are authored by the user (사민경) with a `Co-Authored-By: Claude` trailer.
- Report outcomes faithfully: actual test evidence, limitations, and what remains unverified.

## Current architecture
- Zero-dependency static web frontend (`web/index.html`, `web/styles.css`, `web/app.js`)
- Node built-in server (`scripts/dev-server.mjs`)
- Tauri 2 wrapper (`src-tauri`)
- Browser localStorage persistence under `jobbit-progress-v1`
- `.claude/skills/` stores AI-agent guidance; skills are NOT runtime app features yet.

## Code areas
- UI: `web/` (HTML, styles, JS)
- Plan import: `scripts/export_plan.py` and `web/data/*.json`
- Desktop native: `src-tauri/`
- Agent guidance: `.claude/skills/` and `docs/`
- CI: `.github/workflows/`
- Shared state schema changes require a versioned migration and QA checklist.

## Verification
- `npm run check` before every PR.
- Windows desktop build is verified by the `windows-build` GitHub Actions job (runs on PRs and manual dispatch). A green CI build proves the app compiles and packages on Windows — it does **not** prove visual/interactive behavior (transparency, click-through, drag). Those stay on the manual checklist in `docs/ROADMAP.md`.
- Manual web QA: start web, check first/last day navigation, step check, status after reload, backup import/export, hostile text escaping, planned days = 166.
- Do not claim Windows behavior was tested based on browser checks.

## Safety and quality
- Do not automatically mark plans complete or send data outside the device.
- Never expose secrets from MCP, browser localStorage, or the user's machine to external services.
- No automatic grading or changing of task status based solely on AI text.
- New AI workflows belong in opt-in integrations.
- Do not install third-party plugin code before inspecting permissions and maintenance.
- Preserve original app branding/artwork; respect MIT attributions if reusing WindowPet code later.

## Skills
Reusable job coaching skills in `.claude/skills/` are **instructions for the coding assistant**. They are not yet wired to run inside the JOBBIT app.
