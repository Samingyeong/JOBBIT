# JOBBIT — Claude Code project instructions

Read this file, then `README.md`, `docs/ROADMAP.md` and the latest entry of `docs/DEVLOG.md` before starting work.

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

## Before opening a PR (required)
1. Run `npm run check` and `npm run lint` (ESLint + jscpd, duplication > 3% fails). If `src-tauri/` changed, also `cargo fmt --check` and `cargo clippy --locked --all-targets -- -D warnings` in `src-tauri/` (needs Tauri Linux deps; otherwise rely on the `rust-lint` CI job and say so).
2. Write the review inputs into `.review/` (gitignored): `diff.patch` (`git add -A && git diff --cached <base> -- . ':!package-lock.json'`, where `<base>` is the PR's base branch — this includes uncommitted and new files), `checks.txt` (actual output of step 1), `scope.md` (roadmap step + intent).
3. Run **both** reviews on the same change:
   - the `pr-reviewer` subagent (`.claude/agents/pr-reviewer.md`, read-only) — JOBBIT-specific checks. Subagents register at session start; if it is not available (e.g. the PR creates or edits it), run the read-only `Explore` agent with the instruction to read `.claude/agents/pr-reviewer.md` and follow it exactly, without Bash, and say so in the PR body.
   - `/code-review` (Anthropic code-review) — general correctness bugs
4. **No PR while any "반드시 수정" item from `pr-reviewer`, or any correctness bug reported by `/code-review`, is open.** Fix them and re-run both reviews.
   - Exception: only if the user explicitly approves opening the PR with a specific item unresolved. Then add a `### 미해결 반드시 수정 (사용자 승인)` subsection to the PR body listing each item with the reason and the user's approval.
5. Paste the final `pr-reviewer` output verbatim into the PR body under `## pr-reviewer 결과`, and the `/code-review` findings (or "no findings") under `## code-review 결과`.

## When a roadmap step ends
Add an entry to `docs/DEVLOG.md` (newest at the top) with three parts: **한 일**, **문제와 해결**, **결정 사항과 이유**. Include it in the step's PR. Keep it factual: what was verified and how, what was not.

## Docs format (Obsidian)
The user opens `docs/` as an Obsidian vault. In `docs/*.md`:
- Use standard Markdown links with relative paths, e.g. `[로드맵](ROADMAP.md)` — never `[[wikilinks]]`.
- Link only between files inside `docs/`; refer to files outside it (e.g. `CLAUDE.md`, `web/app.js`) as inline code, since `../` links don't resolve inside the vault.
- `docs/.obsidian/` is the user's local vault config and is gitignored.

## Verification
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
