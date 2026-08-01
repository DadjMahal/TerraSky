# Prompt Logging

Every task performed by Cline must be logged.

## Location

All execution logs are stored in:

```
Documentation/logs/
```

## File naming

```
YYYY-MM-DD_<short-task-slug>.md
```

Example: `2026-07-29_skydash-multicloud-refactor.md`

## Required sections

Each log file must include:

- **Date and time** — when the task started / finished.
- **User prompt** — the original request (quoted or summarized).
- **Actions performed** — step-by-step list of what was done.
- **Errors** — any errors encountered and how they were resolved (or "None").
- **Result** — final outcome and how it was verified.

## Language

Logs are written in **English** (per `REQUIREMENTS.md`).
