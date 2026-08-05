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


