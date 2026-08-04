# 🚀 START HERE — SkyDash (read this first, every session)

> **Fast orientation (~800 tokens).** For full project history & near-context read
> `Documentation/SESSION_HANDOFF.md` (once per session, ~2–3k tokens). This file
> is the fast entry point + routing table + reality-check. Rules live in
> `AGENT_ONBOARDING.md`; deep context is read **on demand** via the routing table.

## ⚠️ Resume check (do this first)

If **`SESSION_IN_PROGRESS.md`** exists at repo root → the last session was
**cut off mid-work** (rate-limited / interrupted). Read it FIRST and **resume** the
"Current step" — don't pick a new task. If absent, continue below.

## Project (one line)

**SkyDash** — lightweight single-server multi-cloud (AWS/Azure/Oracle/Alibaba)
dashboard that reads the Terraform inventory and manages 7 VMs via each cloud's
official Python SDK. Flask on :8080, nginx reverse-proxy on :80, deployed via
GitHub Actions.

## ✅ Reality check (paste output BEFORE claiming anything works)

```bash
scripts/status.sh          # one-shot live state (service + nginx + login HTTP)
# or manually:
systemctl is-active skydash.service
ss -tlnp 2>/dev/null | grep -E ':80 |:8080 '     # expect both LISTEN
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/login   # expect 200
curl -s http://localhost/login | grep -o '<title>[^<]*</title>'   # SkyDash
cd /home/volodro && git log --oneline -5                         # recent work
```

## 🧭 Routing table (read ONLY the file your task touches)

| Task touches                       | Read first                                                            |
|------------------------------------|-----------------------------------------------------------------------|
| Anything / every session           | `START_HERE.md` (this), `AGENT_ONBOARDING.md` (rules)                  |
| Full state & progress              | `Documentation/SESSION_HANDOFF.md` (once per session)                  |
| Pick a task / task status          | `TASKS.md` (board)                                                     |
| Live deployed status               | `STATUS.md` + run `scripts/status.sh`                                  |
| UI/UX Dashboard (tasks 1–10)       | `skydash/docs/task_planning/01_ux_shutek_dashboard.md`                 |
| UI/UX Detail pages (11–20)         | `skydash/docs/task_planning/02_ux_shutek_detail_pages.md`              |
| Hermes agent (26–40)               | `skydash/docs/task_planning/03_agent_hermes_integration.md` + `hermes_agent.py` |
| Cline agent (27–41)                | `skydash/docs/task_planning/04_agent_cline_integration.md`             |
| Error logging (42–61)              | `skydash/docs/task_planning/05_error_logging_system.md` + `app.py` caching |
| Cloudflare (61–72)                 | `skydash/docs/task_planning/06_cloudflare_integration.md`              |
| Live monitoring (73–82)            | `skydash/docs/task_planning/07_live_monitoring.md`                     |
| Backups (83–90)                    | `skydash/docs/task_planning/08_backup_system.md`                       |
| Ports/security groups (91–100)     | `skydash/docs/task_planning/09_port_management.md`                     |
| Providers / business logic         | `skydash/providers/registry.py` + each `providers/<cloud>.py`          |
| Auth / config store                | `skydash/auth.py`, `skydash/config_store.py`                           |
| Routes / Flask layer               | `skydash/app.py`                                                       |
| CI/CD / deployment                 | `.github/workflows/deploy.yml` + `deploy/nginx/skydash.conf`           |

## 📜 The 7 Hard Rules (full text in AGENT_ONBOARDING.md)

1. **Verify before claim** — no "working" without pasted command output.
2. **No fake logs** — status from real commands (systemctl, curl, ss), never invented.
3. **Usage validation** — a class isn't done unless something calls its methods.
4. **Audit-first** — read the matching task doc before writing code.
5. **Document before code** — write the doc, then implement.
6. **Leave cleaner** — remove dead code, update stale docs.
7. **Milestone doc-sync** — after EVERY milestone update the knowledge base
   (this file, `STATUS.md`, `SESSION_HANDOFF.md`, `TASKS.md`) and git-commit,
   even mid-session (see `Documentation/WORKFLOW.md` §3).

## ⚡ Quick Start

```bash
cd /home/volodro && bash scripts/session_start.sh   # orients + resume-aware
bash scripts/session_end.sh                          # sync knowledge base + commit
bash scripts/status.sh                               # live state (reality check)
```
