# Codex / Claude Code handoff

## Ready-to-paste task

You are extending the existing JOBBIT starter. First read `AGENTS.md`, `README.md`, and inspect `web/data/plan.json` and the existing functional UI. Do NOT rewrite the app from scratch. Preserve all 166 actual dated tasks, completion tracking, notes, import/export and offline-first behavior.

Goal (first PR): Implement the Windows desktop experience using Tauri 2 with **two separate windows**: a small always-on-top transparent pet overlay and a normal task/dashboard panel that opens when the pet is clicked. Make the pet draggable without obscuring unrelated desktop interactions. Investigate click-through constraints using official Tauri docs and explicit capability permissions; do not guess APIs. Allow turning always-on-top off. Keep the current localStorage schema compatible or implement a documented migration. Add tests for navigation, persistence, escaping and completion logic. Provide Windows build instructions and test results; if you cannot build on Windows, say so.

Workflow:
1. Propose architecture and files to modify.
2. Implement only the first PR scope and log assumptions.
3. Run `npm run check` and applicable Tauri build checks.
4. Report changed files, tests actually run, known risks, manual QA steps.
5. Never claim success without verified results.

Second PR, only after first verified: SQLite storage, migration, OS notification settings, GitHub evidence permission prompts. Third PR: `daily-planner`, `task-evaluator`, `interview-simulator`, `weekly-retrospective` as opt-in agent integrations with evaluations and cost controls.

## Recommended Claude Code plugins (choose the minimal set)
- `frontend-design`
- `superpowers`
- `context7`
- `playwright`
- `github`
- Optional: `feature-dev`, `code-review`
Use `/plugin` discover panel and confirm availability before installation.

## POC acceptance checklist
- [ ] Transparent pet window displays on Windows above other apps
- [ ] Can drag pet across screen
- [ ] Clicking pet opens today task panel
- [ ] Can close task panel without quitting pet
- [ ] All 166 seeded days preserved
- [ ] Check state, notes, evidence persisted after restart
- [ ] Doesn't swallow clicks outside visible pet
- [ ] Can disable always-on-top
- [ ] No AI runtime needed to operate TODOs
- [ ] Build/tests verified on Windows
