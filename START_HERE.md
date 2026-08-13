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

| Task touches                                | Read first                                                            |
|---------------------------------------------|-----------------------------------------------------------------------|
| Anything / every session                    | `START_HERE.md` (this), `AGENT_ONBOARDING.md` (rules)                 |
| Full state & progress                       | `STATUS.md` + run `scripts/status.sh`                                 |
| Architecture audit / spec coverage (144 §) | `docs/architecture-gap-analysis.md` (NEW — full §1–144 classification) |
| Iteration planning (10 iterations)          | `docs/iteration-plan.md` (NEW — maps tasks to spec sections)           |
| Domain model & entities                     | `docs/domain-model.md` (NEW)                                          |
| Provider framework / SDK                    | `docs/provider-framework.md` (NEW) + `skydash/providers/`              |
| Security model & hardening                  | `docs/security-model.md` (NEW) + `AGENT_ONBOARDING.md`                |
| Terraform integration                       | `docs/terraform-integration.md` (NEW)                                  |
| API design                                  | `docs/api-reference.md` (NEW)                                         |
| UI/UX design & wireframes                   | `skydash/docs/FRONTEND_HANDBOOK.md` (current design system) + `docs/ui-wireframes.md` (NEW) |
| Deployment topology                         | `docs/infrastructure-diagram.md` (NEW)                               |
| Pick a task / task status                   | `TASKS.md` (board)                                                    |
| Old planning docs (historical, 100-task)    | `skydash/docs/task_planning/` — Category 1–9 docs (superseded by iteration plan for new work) |
| Auth / config store                         | `skydash/auth.py`, `skydash/config_store.py`                          |
| Routes / Flask layer                        | `skydash/app.py`                                                      |
| CI/CD / deployment                          | `.github/workflows/deploy.yml` + `deploy/nginx/skydash.conf`          |
| Live deployed status                        | `STATUS.md` + run `scripts/status.sh`                                 |

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

## 🔄 Iteration workflow (new)

The project has transitioned from the old 100-task board (`TASKS.md` Categories
1–9) to a **spec-driven 10-iteration plan** mapped to all 144 sections of the
`Multi-Cloud Infrastructure Management Framework.md`.

| Iter | Focus | Status | Key Doc |
|------|-------|--------|---------|
| **0** | Architecture audit + gap analysis | ✅ Complete | `docs/architecture-gap-analysis.md` |
| 1 | CSRF, rate limiting, API v1, OpenAPI, error codes | ✅ Complete | `docs/iteration-plan.md` |
| 2 | Provider capabilities, status model, drift detection | 🔄 Active | `docs/provider-framework.md` |
| 3 | Secrets migration, RBAC, audit logging | ⏸️ Backlog | — |
| 4 | UI safety, activity timeline, notifications | ✅ Complete | — |
| 5 | Terraform integration (state, drift, plan/apply UX) | 🔄 Active | `docs/terraform-integration.md` |
| 6 | Structured logging, Prometheus + Grafana | ⏸️ Backlog | — |
| 7 | Alerts, inventory, relationships graph | ✅ Complete | — |
| 8 | Project/Environment entities, Application model | 🔄 Active | `docs/domain-model.md` |
| 9 | OPA policy engine, multi-tenancy, GitOps | ⏸️ Backlog | — |
| 10 | Production hardening (⛔ REQUIRES USER DECISION) | ⏸️ Backlog | — |

> **Backlog rationale:** Iter 3 (Vault migration) awaits Iter 10 external
> secrets backend; Iter 6 (structured logging) overlaps with Iter 10's
> observability infra (Prometheus/Grafana already live); Iter 9 (OPA) needs the
> external `opa`/`conftest` binary; Iter 10 (hardening) already has infra live
> but Vault/KMS remains staged.
> **Total Terraform integration** (all commands, remote backends, OPA/Conftest,
> Sentinel) is NOT covered by the current plan — it's a 3-iteration expansion
> detailed in `docs/terraform-integration.md`.

## ⚡ Quick Start

```bash
cd /home/volodro && bash scripts/session_start.sh   # orients + resume-aware
bash scripts/session_end.sh                          # sync knowledge base + commit
bash scripts/status.sh                               # live state (reality check)
```

## 🚀 Deployment (CI/CD — GitHub Actions)

SkyDash is deployed via **GitHub Actions** to a local server (no manual deployment needed).
Just push to `main` and the workflow handles everything:

```bash
git add .
git commit -m "your changes"
git push origin main    # GitHub Actions auto-deploys
```

**What the CI/CD pipeline does:**
1. Validates Python syntax (pre-deploy gate)
2. `rsync` files to server at `167.172.188.248` (user: `volodro`)
3. Configures nginx reverse-proxy (port 80 → Flask 8080)
4. Installs Python deps in venv, restarts `skydash.service` via systemd
5. Health check: HTTP 200 + "SkyDash" title on port 80

**Server:** `digital-2` @ `167.172.188.248` (was `74.248.232.219` — IP updated 2026-08-13)
**SSH:** `volodro` user, ED25519 deploy key (regenerated 2026-08-13)
**GitHub secrets:** `SERVER_IP` (updated), `SSH_PRIVATE_KEY` (updated), `HERMES_SSH_KEY` (Hermes agent)

> **Note:** If you need to deploy manually (e.g., CI/CD is broken):
> 1. `cp /root/TerraSky/skydash/* /home/volodro/skydash/`
> 2. `rm -rf /home/volodro/skydash/__pycache__/`
> 3. `systemctl restart skydash.service`
> 4. Verify: `systemctl is-active skydash.service` + `curl -s https://localhost/login`
