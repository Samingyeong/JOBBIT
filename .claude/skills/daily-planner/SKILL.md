---
name: daily-planner
description: Review and propose a realistic day or week study plan from JOBBIT's dated 2027 job preparation plan without silently changing the source or actual progress.
---
# JOBBIT Daily Planner

## Inputs
- `web/data/plan.json`: the approved day-by-day plan
- User-provided date, available time and current progress (if supplied)
- Explicit constraints such as interview deadlines

## Workflow
1. Identify the current day's planned entry and nearby overdue entries.
2. Preserve the job-track allocation unless a specific upcoming hiring event requires a change.
3. Pick up to three tasks with stated time budget and measurable acceptance criteria.
4. Explain what moved and why, separating reported progress from assumptions.
5. Present adjustments as a **proposal**. Never edit plan or mark complete without explicit user approval.

## Output
Markdown table: day, task, planned minutes, deliverable, proof, risk. End with one concrete next action.
