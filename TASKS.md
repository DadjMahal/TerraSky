# 📋 TASKS — SkyDash Task Board (live)

> Live board of all 100 planned tasks. Claim a task: set status `in_progress` +
> owner, work it, verify, then set `done` + Result + Evidence. Detail for each task
> lives in `skydash/docs/task_planning/`. Rules: `AGENT_ONBOARDING.md` / `WORKFLOW.md`.

## Legend

| Status | Meaning |
|--------|---------|
| ⬜ `pending` | Not started / available to claim |
| 🔵 `in_progress` | Being worked on (set owner) |
| ✅ `done` | Completed + verified (with Evidence) |
| 🔴 `blocked` | Blocked — needs resources/user input |

---

## Category 1 — UI/UX Dashboard (10)

| # | Task | Status | Owner | Result / Evidence |
|---|------|--------|-------|-------------------|
| 1 | Dashboard — adaptive design | ✅ done | Cline | base.html/index.html updated, deployed (2026-08-02) |
| 2 | Dark/Light Mode Toggle | ✅ done | Cline | theme toggle in navbar; live on 74.248.232.219 |
| 3 | CSS animations (hover/fade) | ✅ done | Cline | fade-in cards, hover gradient; deployed |
| 4 | Interactive region map | ✅ done | Cline | Leaflet.js map w/ provider-coloured markers; toggle in navbar; `region-map.js` (2026-08-04) |
| 5 | Enhanced tag filters | ✅ done | Cline | multi-select tag dropdown + type/region filters; `dashboard.js` (2026-08-04) |
| 6 | Drag-and-drop reordering | ✅ done | Cline | Sortable.js reorder saved to localStorage; (2026-08-04) |
| 7 | CPU/RAM load visualization | ✅ done | Cline | progress bars via new `/api/load` endpoint (fleet-relative); (2026-08-04) |
| 8 | Toast notifications w/ animation | ✅ done | Cline | animated toast stack + auto-dismiss; `dashboard.js`/`dashboard.css` (2026-08-04) |
| 9 | Quick Actions context menu | ✅ done | Cline | right-click menu (Start/Stop/Refresh/Details/Logs); `dashboard.js` (2026-08-04) |
| 10 | Infinite scroll / pagination | ✅ done | Cline | IntersectionObserver infinite scroll + "Load more" button; (2026-08-04) |

## Category 2 — UI/UX Detail Pages (10)

| # | Task | Status | Owner | Result / Evidence |
|---|------|--------|-------|-------------------|
| 11 | Detail page with tabs | ✅ done | Cline | tabbed detail (Overview/Hardware/Network/Actions/Timeline/Logs/Metrics/Domains/SSH); `detail.html` (2026-08-04) |
| 12 | Progress loader for actions | ✅ done | Cline | staged animated action loader; `detail.js` (2026-08-04) |
| 13 | Hardware specs visualization | ✅ done | Cline | SVG CPU/RAM/Disk gauges; `specs-visualization.js` (2026-08-04) |
| 14 | Network topology map | ✅ done | Cline | SVG topology (Internet→pub/priv IP/DNS); `topology.js` (2026-08-04) |
| 15 | Status change timeline | ✅ done | Cline | horizontal timeline from `/api/status-history` (status_history.py); `status-timeline.js` (2026-08-04) |
| 16 | Built-in SSH terminal | ✅ done | Cline | xterm.js + Flask-SocketIO ↔ paramiko bridge for Hermes; `ssh_bridge.py`+`ssh-terminal.js` (2026-08-04) |
| 17 | Log viewer w/ syntax highlight | ✅ done | Cline | color-coded level highlight; `.log-viewer` CSS (2026-08-04) |
| 18 | Metrics charts for instance | ✅ done | Cline | Chart.js CPU/RAM/disk (+ live disk for Hermes); `/api/metrics`; `metrics-charts.js` (2026-08-04) |
| 19 | Custom domain mapping UI | ✅ done | Cline | domain tab UI + CRUD via `/api/domains` persisted in config_store (2026-08-04) |

> **2026-08-05 — full visual redesign applied on top of Categories 1 & 2.**
> Every task above is still accurately `done` (the *features* Cline built —
> theme toggle, region map, drag-drop, context menu, tabs, gauges, SSH
> terminal, etc. — are all still present and functional). What changed is
> purely visual: colors, typography, spacing, icons (emoji → Bootstrap
> Icons), and a new shared token system. Owner: Claude (Anthropic). Not yet
> deployed/click-tested — see `STATUS.md` § In Progress and
> `skydash/docs/FRONTEND_HANDBOOK.md` for scope, rationale, and the
> pre-deploy verification checklist. **Read the handbook before starting any
> new task in Category 1 or 2**, or any future UI work — it's now the
> authoritative frontend spec.

## Category 3 — Hermes Agent (15)

| # | Task | Status | Owner | Result / Evidence |
|---|------|--------|-------|-------------------|
| 26 | Agent state indicator widget | ⬜ pending | | |
| 27 | Built-in SSH terminal | ⬜ pending | | |
| 28 | Remote command exec + history | ⬜ pending | | |
| 29 | SSH file manager | ⬜ pending | | |
| 30 | File upload/download | ⬜ pending | | |
| 31 | Real-time process monitor | ⬜ pending | | |
| 32 | Network activity graphs | ⬜ pending | | |
| 33 | System resource usage (CPU/RAM/Disk) | ⬜ pending | | |
| 34 | System restart/shutdown control | ⬜ pending | | |
| 35 | Config cloning capability | ⬜ pending | | |
| 36 | System settings backup/restore | ⬜ pending | | |
| 37 | Multi-agent manager dashboard | ⬜ pending | | |
| 38 | Agent audit trail logging | ⬜ pending | | |
| 39 | Emergency stop button | ⬜ pending | | |
| 40 | Agent health check automation | ⬜ pending | | |

## Category 4 — Cline Agent (15)

| # | Task | Status | Owner | Result / Evidence |
|---|------|--------|-------|-------------------|
| 27 | Cline task execution interface | ⬜ pending | | |
| 28 | Task queue w/ progress bar | ⬜ pending | | |
| 29 | Cline data flow visualization | ⬜ pending | | |
| 30 | Task management interface | ⬜ pending | | |
| 31 | Cline logs searchable | ⬜ pending | | |
| 32 | Cline webhook integration | ⬜ pending | | |
| 33 | Cline template system | ⬜ pending | | |
| 34 | Task scheduling system | ⬜ pending | | |
| 35 | Cline notification system | ⬜ pending | | |
| 36 | Cline error recovery | ⬜ pending | | |
| 37 | Parallel execution control | ⬜ pending | | |
| 38 | Env vars manager | ⬜ pending | | |
| 39 | Cline output visualization | ⬜ pending | | |
| 40 | Git repository integration | ⬜ pending | | |
| 41 | Cline code quality checks | ⬜ pending | | |

## Category 5 — Error Logging System (20)

| # | Task | Status | Owner | Result / Evidence |
|---|------|--------|-------|-------------------|
| 42 | Centralized logging (ELK) | ⬜ pending | | |
| 43 | Structured JSON logging | ⬜ pending | | |
| 44 | Log levels + custom handlers | ⬜ pending | | |
| 45 | Log rotation/retention | ⬜ pending | | |
| 46 | Log correlation ID | ⬜ pending | | |
| 47 | Real-time log streaming | ⬜ pending | | |
| 48 | Advanced log search | ⬜ pending | | |
| 49 | Log alerting system | ⬜ pending | | |
| 50 | Anomaly detection | ⬜ pending | | |
| 51 | Log dashboard | ⬜ pending | | |
| 52 | Error grouping/clustering | ⬜ pending | | |
| 53 | Traceback visualization | ⬜ pending | | |
| 54 | Log export (CSV/JSON/PDF) | ⬜ pending | | |
| 55 | Log comparison between instances | ⬜ pending | | |
| 56 | Performance metrics logging | ⬜ pending | | |
| 57 | Audit trail for admin actions | ⬜ pending | | |
| 58 | Security event logging | ⬜ pending | | |
| 59 | Health check endpoints | ⬜ pending | | |
| 60 | Synthetic transaction monitoring | ⬜ pending | | |

## Category 6 — Cloudflare Integration (12)

| # | Task | Status | Owner | Result / Evidence |
|---|------|--------|-------|-------------------|
| 61 | Cloudflare API integration | ⬜ pending | | |
| 62 | DNS records management | ⬜ pending | | |
| 63 | SSL/TLS certificate management | ⬜ pending | | |
| 64 | DDoS protection config | ⬜ pending | | |
| 65 | Firewall rules manager | ⬜ pending | | |
| 66 | Workers deployment control | ⬜ pending | | |
| 67 | CDN configuration | ⬜ pending | | |
| 68 | Page Rules management | ⬜ pending | | |
| 69 | Zone settings | ⬜ pending | | |
| 70 | Argo Tunnel integration | ⬜ pending | | |
| 71 | Access Policies | ⬜ pending | | |
| 72 | Cloudflare analytics dashboard | ⬜ pending | | |

## Category 7 — Live Monitoring (10)

| # | Task | Status | Owner | Result / Evidence |
|---|------|--------|-------|-------------------|
| 73 | htop-style interface | ⬜ pending | | |
| 74 | Real-time CPU/Mem/Disk | ⬜ pending | | |
| 75 | Network activity graphs | ⬜ pending | | |
| 76 | Process tree visualization | ⬜ pending | | |
| 77 | File system activity | ⬜ pending | | |
| 78 | System calls tracing | ⬜ pending | | |
| 79 | Container/resource usage | ⬜ pending | | |
| 80 | Alert history dashboard | ⬜ pending | | |
| 81 | Custom metric agents | ⬜ pending | | |
| 82 | Historical data viz | ⬜ pending | | |

## Category 8 — Backup System (8)

| # | Task | Status | Owner | Result / Evidence |
|---|------|--------|-------|-------------------|
| 83 | Full instance backup | ⬜ pending | | |
| 84 | Incremental backup | ⬜ pending | | |
| 85 | Backup retention policies | ⬜ pending | | |
| 86 | Backup encryption | ⬜ pending | | |
| 87 | Restore to different instance | ⬜ pending | | |
| 88 | Automated backup scheduling | ⬜ pending | | |
| 89 | Backup verification/integrity | ⬜ pending | | |
| 90 | Disaster recovery plan | ⬜ pending | | |

## Category 9 — Port/Permission Management (10)

| # | Task | Status | Owner | Result / Evidence |
|---|------|--------|-------|-------------------|
| 91 | Security groups mgmt (all clouds) | ⬜ pending | | |
| 92 | Inbound/Outbound rules | ⬜ pending | | |
| 93 | Port ranges w/ validation | ⬜ pending | | |
| 94 | IP whitelist/blacklist | ⬜ pending | | |
| 95 | Security group templates | ⬜ pending | | |
| 96 | Auto security group generation | ⬜ pending | | |
| 97 | VPN tunnel management | ⬜ pending | | |
| 98 | Firewall rules history | ⬜ pending | | |
| 99 | Compliance checking | ⬜ pending | | |
| 100 | Breach detection + alerting | ⬜ pending | | |

## 📥 Backlog (deferred / needs resources)

> Items moved out of the active path. Re-prioritise when bandwidth allows.

| Item | Origin | Reason deferred |
|------|---------|------------------|
| Set secure `SKYDASH_ADMIN_PASSWORD` (server venv `terraform/.env`) | STATUS.md next-step #2 | Skipped per user request 2026-08-04; security hardening, not feature work |

---

## 🔄 Iteration-Based Task Board (NEW — replaces Category 1–9 for new work)

> Based on §134 (Development Phases), §141 (Engineering Phases), and the
> 144-section gap analysis. See `docs/iteration-plan.md` for the full roadmap.
> The old 100-task board above is preserved for historical reference.

### Iteration 0 — Architecture Audit & Gap Analysis ✅ COMPLETE

| # | Task | Status | Owner | Result / Evidence |
|---|------|--------|-------|-------------------|
| task_0001 | Create `docs/` directory + gap analysis | ✅ done | lead | `docs/architecture-gap-analysis.md` — all 144 sections classified |
| task_0002 | Domain model doc | ✅ done | lead | `docs/domain-model.md` — entities mapped to code |
| task_0003 | Provider framework + security + Terraform docs | ✅ done | lead | 3 docs created |
| task_0004 | API reference + UI wireframes docs | ✅ done | lead | 2 docs created |
| task_0005 | Infrastructure diagram + iteration plan | ✅ done | lead | 2 docs created |
| task_0006 | Update START_HERE.md + STATUS.md + TASKS.md | ✅ done | lead | Knowledge base synced, committed |

### Iteration 1 — CSRF, Rate Limiting, API v1, OpenAPI, Error Codes

| # | Task | Status | Owner | § | Evidence |
|---|------|--------|-------|---|----------|
| task_0007 | Add CSRF protection (Flask-WTF) on all POST routes | ✅ done | Cline | §77 | CSRFProtect(app) + hidden form tokens in login/admin + `/api/csrf-token` + `static/js/csrf-header.js` AJAX interceptor; py_compile OK |
| task_0008 | Add rate limiting (Flask-Limiter) on auth + API | ✅ done | Cline | §76 | `auth.py` limiter (login 5/min, admin mutations 10-30/hr); py_compile OK |
| task_0009 | Add `/api/v1/` versioning prefix | ✅ done | Cline | §62 | `api_v1` Blueprint + `X-API-Version: deprecated` header on legacy `/api/` (app.py) |
| task_0010 | Generate OpenAPI 3.0 spec from routes | ✅ done | Cline | §125 | `skydash/openapi.py` (build_spec, valid JSON) + `/api/v1/openapi.json` + `/api/v1/docs` Swagger UI in app.py; py_compile + route-coverage check OK. CLI (§63) added in `skydash/cli.py` (list/status/start/stop) |

### Iteration 2 — Provider Capabilities, Drift Detection

| # | Task | Status | Owner | § | Evidence |
|---|------|--------|-------|---|----------|
| task_0011 | Extend `CloudProvider` with `get_capabilities()` | ✅ done | Cline | §2.2, §10 | `providers/base.py` capabilities + per-provider declarations + `GET /api/v1/providers` (registry import verified) |
| task_0012 | Add drift detection (tfstate vs live comparison) | ✅ done | Cline | §15 | `drift.py` compare/detect/summarize + `GET /api/v1/drift`; unit-tested (unavailable providers → honest "unverifiable"); live sweep needs cloud creds (deploy) |
| task_0013 | Standardize status model (use `models.py` constants everywhere) | ⬜ pending | | §43 | |

### Iteration 3 — Secrets Migration, RBAC, Audit Logging

| # | Task | Status | Owner | § | Evidence |
|---|------|--------|-------|---|----------|
| task_0014 | Migrate secrets to Vault/Secrets Manager | 🔵 partial | Cline | §29, §69 | `crypto.py` AES-256-GCM seal/unseal + `SKYDASH_SECRETS_KEY` convention (runtime-tested); Vault/KMS backend BLOCKED — external service (Iter 10) |
| task_0015 | Implement RBAC roles (admin/user/read-only) | ✅ done | Cline | §33, §34 | `rbac.py` (admin/operator/readonly hierarchy, require_role/require_permission → 403 FORBIDDEN) wired onto all admin routes; escalation bug found+fixed in review; unit-tested |
| task_0016 | Add audit logging (structured, append-only) | ✅ done | Cline | §37, §81 | `audit.py` append-only JSONL + SHA-256 hash chain, `@audited` on mutating admin + instance-action routes, query + verify_chain; tamper-detection unit-tested |

### Iteration 4 — UI Safety, Activity Timeline, Notifications

| # | Task | Status | Owner | § | Evidence |
|---|------|--------|-------|---|----------|
| task_0017 | Danger-zone separation for destroy/reboot | ✅ done | Cline | §86 | detail.html Danger zone (stop moved, typed-confirm modal w/ §107 approval token) + managed/unmanaged badge; `node --check` OK |
| task_0018 | Activity timeline (§87) | ✅ done | Cline | §87 | status-timeline tab already shipped (`status_history.py` + `status-timeline.js`); retro-added `recent_events()` assistant, unit-tested |
| task_0019 | Notification center / toast system | ✅ done | Cline | §60 | navbar bell + `static/js/notifications.js` consuming `GET /api/v1/notifications` (status events, newest-first, unit-tested) |

### Iteration 5 — Terraform Integration

| # | Task | Status | Owner | § | Evidence |
|---|------|--------|-------|---|----------|
| task_0020 | tfstate reading + basic drift (§11) | ⬜ pending | | §11, §15 | |
| task_0021 | Workspace model (design) (§12) | ⬜ pending | | §12 | |
| task_0022 | State security (design) (§13) | ⬜ pending | | §13 | |
| task_0023 | Provider sync cron (§42) | ⬜ pending | | §42 | |
| task_0024 | Plan/apply UX read-only (§102-104) | ⬜ pending | | §102-104 | |

> **Terraform scope question:** "Total Terraform integration" (all commands,
> remote backends, modules, OPA/Conftest, Sentinel) is NOT in Iter 5.
> See `docs/terraform-integration.md`. **Awaiting user decision.**

### Iteration 6 — Logging, Prometheus, Grafana

| # | Task | Status | Owner | § | Evidence |
|---|------|--------|-------|---|----------|
| task_0025 | Structured logging | ⬜ pending | | §81 | |
| task_0026 | Prometheus metrics endpoint | ⬜ pending | | §45, §82 | |
| task_0027 | Grafana dashboard config | ⬜ pending | | §82 | |

### Iteration 7 — Alerts, Inventory, Relationships

| # | Task | Status | Owner | § | Evidence |
|---|------|--------|-------|---|----------|
| task_0028 | Alert thresholds + dispatch | ✅ done | Cline | §46 | `health.py` data-driven threshold rules + `GET /api/v1/alerts`; dispatch (SMTP/webhook) BLOCKED on infra | 
| task_0029 | Global inventory view | ✅ done | Cline | §57 | `inventory.py` indexed search (slug/name/provider/region/type/status/tags) + `GET /api/v1/inventory?q=` + CSV report (§92) |
| task_0030 | Resource relationships graph | ⬜ pending | | §88, §89 | |

### Iteration 8 — Project/Environment, Application Model

| # | Task | Status | Owner | § | Evidence |
|---|------|--------|-------|---|----------|
| task_0031 | Project + Environment entities | ⬜ pending | | §6.1, §105 | |
| task_0032 | Application model + deployment engine | ✅ done | Cline | §25-27 | `deployments/applications.py` + `/api/v1/applications/*/deployments`; rollback + prod approval gate wired; unit-tested (real host builds BLOCKED on deploy infra) |

### Iteration 9 — OPA Policy Engine, Multi-Tenancy, GitOps

| # | Task | Status | Owner | § | Evidence |
|---|------|--------|-------|---|----------|
| task_0033 | OPA/Conftest policy gate on plans | 🔵 partial | Cline | §67-68 | in-process `policy.py` (policies-as-data evaluate/allowed + prod_shield on start/stop); OPA/Conftest engine BLOCKED — external binary not installed |
| task_0034 | Multi-tenancy (Org/Project isolation) | ⬜ pending | | §35-36 | |
| task_0035 | GitOps workflow | ⬜ pending | | §65, §66 | |

### Iteration 10 — Production Hardening ⛔ REQUIRES USER DECISION

| # | Task | Status | Owner | § | Evidence |
|---|------|--------|-------|---|----------|
| task_0036 | External services budget approval | ✅ complete | user | § | Owner approved (2026-08-12); core infra provisioned & live on the droplet |
| task_0037 | Deploy PostgreSQL + Redis + Prometheus + Grafana (+ Vault) | 🔵 partial | Cline | §119, §82 | **Live:** PostgreSQL 16 (skydash db+role), Redis 7 (PONG), Prometheus 2.45.3 (skydash job UP), Grafana (datasource+dashboard provisioned). See docs/db-setup.md + docs/observability.md. **Vault/KMS** external secrets backend remains staged (crypto uses env-passphrase key) |


