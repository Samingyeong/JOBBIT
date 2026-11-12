# JOBBIT Codebase Guide for Codex / Claude Code

## Product
Offline-first career prep desktop companion. The seed is 166 days of a real approved master plan under `web/data/plan.json`; do not regenerate, flatten or overwrite it without approval.

## Current architecture
- Zero-dependency static web frontend (`web/index.html`, `web/styles.css`, `web/app.js`)
- Node built-in server (`scripts/dev-server.mjs`)
- Tauri 2 wrapper (`src-tauri`)
- Browser localStorage persistence under `jobbit-progress-v1`
- `.claude/skills/` stores AI-agent guidance; skills are NOT runtime app features yet.

## Ownership / dependency rules
- UI: `web/` (HTML, styles, JS)
- Plan import: `scripts/export_plan.py` and `web/data/*.json`
- Desktop native: `src-tauri/`
- Agent guidance: `.claude/skills/` and `docs/`
- Shared state schema changes require a versioned migration and QA checklist.
- Make small PRs; don't edit another workstream's owned files without communicating.

## Verification
- `npm run check` before PR.
- Manual QA: start web, check first/last day navigation, step check, status after reload, backup import/export, hostile text escaping, planned days = 166.
- Windows-specific Tauri desktop features require testing on Windows; do not claim tested by running browser checks.

## Next features in order
1. Test real Windows build and fix packaging/asset issues
2. Separate transparent pet window + task panel window; test click-through and drag
3. Migrate state to SQLite with a one-time import from localStorage
4. Use GitHub evidence with explicit auth and user consent
5. Add skill/agent integration as an opt-in service with evaluation and logs

## Safety and quality
- Never expose secrets from MCP, browser localStorage, or user machine to external agents.
- No automatic grading or changing of task status based solely on AI text.
- Do not install random third-party plugin code before inspecting permissions and maintenance.
- Preserve original app branding/artwork; respect MIT attributions if reusing WindowPet code later.
