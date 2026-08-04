# 🤖 SkyDash Agent Onboarding

> Read `START_HERE.md` first for current state + routing table + reality-check.
> This file holds the **rules only**. Full process in `Documentation/WORKFLOW.md`.
> If `SESSION_IN_PROGRESS.md` exists at repo root, **resume it** first.

## Project Summary

**SkyDash** — multi-cloud infrastructure management panel. Manages 7 VMs across
AWS, Azure, Oracle Cloud and Alibaba from a single Flask dashboard. Reads the
static inventory from `terraform/terraform.tfstate`, fetches live power state and
performs start/stop via each cloud's official Python SDK (lazy-imported to save RAM).

- **Stack:** Flask (app.py) · 4 provider SDKs (providers/) · nginx + systemd · GitHub Actions
- **Server:** Ubuntu 24.04, 1 GB RAM, no Docker
- **Honest status:** live on http://74.248.232.219/ via nginx→systemd Flask (see STATUS.md)

## The 7 Hard Rules

1. **Verify before claim** — never say "working" without pasted command output
   (`scripts/status.sh`, `curl`, `systemctl`, etc.).
2. **No fake logs** — all status from real commands/DB/log greps; no invented data.
3. **Usage validation** — a class isn't "complete" unless something calls its
   public methods (grep callers).
4. **Audit-first** — for any area, read the matching task/doc first (routing table).
5. **Document before code** — write the doc, then implement.
6. **Leave cleaner** — remove dead code, update stale docs, leave the repo better.
7. **Milestone doc-sync** — after EVERY milestone update the knowledge base
   (`START_HERE.md`, `STATUS.md`, `SESSION_HANDOFF.md`, `TASKS.md`) and git-commit,
   even if the whole session isn't finished. A fresh session must never read stale context.

## Token budget (per session)

| Type                | Budget    |
|---------------------|-----------|
| Docs only           | 500–1.5k  |
| Code + docs         | 2–5k      |
| Full feature        | 5–10k     |
| Audit deep dive     | 1.5–3k    |

Bootup (`START_HERE.md` + this file) target **≤ ~1,200 tokens**.

## Quick Start

```bash
cd /home/volodro && bash scripts/session_start.sh   # orients + resume-aware
bash scripts/status.sh                                # live state
```

Routing table + reality-check commands live in `START_HERE.md`.
Full process/rules in `Documentation/WORKFLOW.md`.
