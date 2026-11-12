# Why this architecture?

## Build once, test the small scope
The user's career learning plan exists. The UI must not hallucinate or regenerate days. Static JSON preserves the approved schedule; localStorage records an independently auditable progress map. User-controlled JSON backup allows offline export without an account.

## Desktop pet layer
WindowPet is an MIT-licensed open source reference for a separate desktop overlay, transparent window, drag, and click-through behavior. This starter **does not copy WindowPet code** and does not implement real always-on-top or click-through yet. Those require real Windows/Tauri integration tests.

## Future data layer
Use SQLite via supported Tauri plugin after testing desktop packaging. Add migration and schema versioning. Keep data local by default. GitHub connections and cloud/AI providers should require explicit user consent and scoped permissions.

## Plugins vs Skills vs runtime
Claude Code marketplace plugins provide developer assistance, not end-user functionality by themselves. `.claude/skills/*/SKILL.md` contains repeatable instructions for Claude Code. To call a model from the desktop app, implement an explicit backend or local agent connector and security approvals; the skills alone are not executable UI features.

## Feature requirements, next releases
- R1: Open pet / click-through / drag / close panel independently / hide taskbar if configured
- R2: SQLite, notifications, autostart, schedule editing with reversible history
- R3: Copilot tools and evaluation, optional GitHub evidence, interview simulator
