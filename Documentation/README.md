# SkyDash — Multi-Cloud Infrastructure Management Panel

> **THIS FILE IS THE PROJECT MEMORY.** Read it first, every time. It contains the
> full project explanation, architecture, file-by-file guide, live task tracking
> (TODO / IN PROGRESS / DONE), and instructions for any AI assistant (Cline /
> Hermes) that works on this project.

---

## 1. What Is This Project?

**SkyDash** is a lightweight, single-server web panel for managing cloud virtual
machines across **four cloud providers** from a single dashboard:

| Provider | SDK | Instances |
|----------|-----|-----------|
| AWS | `boto3` (EC2) | Hermes, Vikunja |
| Azure | `azure-identity` + `azure-mgmt-compute` | Terraform, MMO_Server, MMSystem |
| Oracle Cloud | `oci` SDK | Hunter |
| Alibaba Cloud | `alibabacloud-ecs20140526` (ECS) | AlibabaPower |

**Total: 7 instances across 4 clouds.**

The panel runs on a **single Ubuntu 24.04 server with 1 GB RAM** (no Docker).
It reads the **static inventory** (names, types, IPs, regions, tags) from the
local Terraform state file, then fetches **live power state** (running/stopped)
and performs **actions** (start/stop) by calling each cloud's API directly via
its official Python SDK.

### Key design principle

**Business logic is 100% provider-independent.** Every cloud provider implements
the same `CloudProvider` interface. The Flask layer and the state reader never
import a concrete provider class or cloud SDK directly — they go through the
provider registry. Adding a new cloud = implement the interface + register it.
SDKs are imported lazily inside provider methods to keep memory low.

---

## 2. Context Checkpoint (SESSION RECOVERY)

> **If you are reading this in a new session, start here.**
> This section is updated after every task. Use it to restore context instantly.

### Current Status

| Item | Status |
|------|--------|
| 🔄 **Last Session Activity** | Task #1-3 implemented: Dark/Light mode toggle, CSS animations (2026-08-02) |
| ✅ **Last Completed Task** | Tasks #1-3: Dashboard UI/UX enhancements - theme toggle, animations, fade-in effects |
| 🎯 **Next Step** | Task #4-5: Interactive region map, enhanced filters, drag-and-drop reordering |
| 📁 **Key Files Modified** | `skydash/templates/base.html`, `skydash/templates/index.html` |
| 📍 **Session Summary** | `skydash/docs/session_summary_100_tasks_2026-08-02.md` |
| 📝 **Execution Log** | `Documentation/logs/2026-08-02_100-tasks-generation-planning.md` |

### How to recover context in a new session:

1. Read this README.md first (you are here)
2. Read `REQUIREMENTS.md` for behavioral rules
3. Read `SPEC.md` for feature goals
4. Read `PROMPT_LOGGING.md` for logging requirements
5. Read the latest session summary in `skydash/docs/`
6. Read the latest execution log in `Documentation/logs/`

---

## 3. Project Structure

```
/home/volodro/
├── terraform/                     # Terraform IaC (source of truth for inventory)
│   ├── .env                       # Cloud credentials (AWS_*, ARM_*, ALICLOUD_*, OCI_*)
│   ├── *.tf                       # Terraform config (aws.tf, azure.tf, oracle.tf, alibaba.tf, main.tf)
│   ├── terraform.tfstate          # Terraform state — SkyDash reads this for inventory
│   └── .terraform/                # Downloaded Terraform providers
│
├── skydash/                       # The Flask web application
│   ├── app.py                     # Flask routes (22 routes: dashboard, detail, API, admin, actions)
│   ├── auth.py                    # Authentication module (login/logout, login_required decorator)
│   ├── config_store.py            # Persistent JSON config (site settings, profile, instance overrides)
│   ├── hermes_agent.py            # SSH-based Hermes Agent log retrieval & disk monitoring
│   ├── models.py                  # Provider-independent Instance dataclass + constants
│   ├── instance_specs.py          # Instance-type → CPU/RAM lookup (fills gaps in TF state)
│   ├── state_reader.py            # Reads terraform.tfstate → list[Instance]
│   ├── app_legacy.py              # Backup of the previous monolithic app (unused)
│   ├── skydash_config.json        # Auto-generated config file (site name, profile, overrides)
│   ├── providers/
│   │   ├── __init__.py            # Package docstring
│   │   ├── base.py               # Abstract CloudProvider interface + shared logic
│   │   ├── aws.py                # AWS provider (boto3)
│   │   ├── azure.py              # Azure provider (azure SDKs)
│   │   ├── oracle.py             # Oracle Cloud provider (oci SDK)
│   │   ├── alibaba.py            # Alibaba Cloud provider (ECS SDK)
│   │   └── registry.py           # Provider key → provider instance mapping
│   ├── templates/
│   │   ├── base.html             # Base template (dark gradient, navbar, footer, flash, toast, modal)
│   │   ├── index.html            # Dashboard (card grid, search/filter/sort, auto-refresh)
│   │   ├── detail.html           # Instance details (overview, hardware, network, actions, logs, Hermes Agent)
│   │   ├── login.html            # Login page (session-based auth, stylish dark gradient)
│   │   ├── admin.html            # Admin panel (site settings, profile, password, instance management)
│   │   ├── 404.html              # 404 Not Found error page
│   │   ├── 503.html              # 503 Server Unavailable error page
│   │   └── instances.html        # Legacy instances list (unused after refactor)
│   ├── docs/
│   │   ├── session_summary_refactor_ui_admin.md  # Session handoff: UI refactor + admin panel
│   │   └── session_summary_2026-07-31.md         # Session summary (all features complete)
│   ├── __pycache__/
│   ├── venv/                     # Python virtual environment
│   └── flask.log                 # Application log
│
├── Documentation/
│   ├── README.md                 # THIS FILE — project memory
│   ├── REQUIREMENTS.md            # Behavioral rules for Cline
│   ├── SPEC.md                   # Feature goals and specifications
│   ├── PROMPT_LOGGING.md          # Logging rules
│   └── logs/
│       ├── 2026-07-29_skydash-multicloud-refactor.md
│       ├── 2026-07-30_skydash-documentation-and-dashboard-fixes.md
│       └── 2026-07-30_auth-hermes-agent-disk.md
│
└── PROMPT_LOGGING.md             # ❌ DUPLICATE — will be removed
```

---

## 4. File-by-File Guide

### `skydash/app.py` — Flask Application (22 routes)
Thin Flask layer with: dashboard, detail page, JSON API for statuses, instance
actions (start/stop), log endpoints, Hermes Agent SSH endpoints, admin panel
routes, error handlers (404/500), context processor for site settings, and
TTL-based status cache (60s). Uses `ThreadPoolExecutor` for parallel status
fetching. Protected by `@login_required` on all routes.

### `skydash/auth.py` — Authentication Module
Session-based auth with `werkzeug.security` password hashing. 1-hour session
timeout. `login_required` decorator. Password verified via `config_store.verify_password()`
(checks stored hash, then env var fallback).

### `skydash/config_store.py` — Persistent Config Store
Reads/writes `skydash_config.json` for: site name/description/favicon/logo,
admin profile (username/email/password hash), hidden instances, instance
display overrides (display_name, description, tags), custom instances.

### `skydash/hermes_agent.py` — Hermes Agent SSH Module
SSH-based (paramiko) log retrieval: Gateway logs, Signal-Cli logs, Command
execution logs, All logs combined. Disk status (`df -h`, `du -sh`, `df -i`).
SSH connection diagnostics (`test_connection`).

### `skydash/models.py` — Instance Model
Provider-independent `Instance` dataclass with fields: slug, name, provider,
region, instance_type, public_ip, private_ip, status, os, cpu, ram, disk,
creation_date, tags, icon, provider_label, can_manage, display_name, extra.

### `skydash/instance_specs.py` — Specs Lookup
Instance-type → CPU/RAM lookup table for AWS (t-series, m-series), Azure
(B-series, D-series, E-series), Oracle shapes, Alibaba ECS types.

### `skydash/state_reader.py` — Terraform State Reader
Parses `terraform.tfstate` → `list[Instance]`, enriches with CPU/RAM from
`instance_specs.py`. Exports `get_instances()`, `get_instance_by_slug()`.

### `skydash/providers/base.py` — Provider Interface
Abstract `CloudProvider` class: `available()`, `get_status()`, `start_instance()`,
`stop_instance()`, `get_logs()`, `scan_logs()`, `get_instance_details()`.

### `skydash/providers/aws.py` — AWS Provider (boto3)
EC2 API: `describe_instances`, `start_instances`, `stop_instances`. Live IP fetch.

### `skydash/providers/azure.py` — Azure Provider
`azure-identity` + `azure-mgmt-compute`. VM instance view for power state.
`begin_start`, `begin_deallocate` (stops billing).

### `skydash/providers/oracle.py` — Oracle Cloud Provider (oci)
`oci` SDK. `get_instance`, `instance_action(START/SOFTSTOP)`.

### `skydash/providers/alibaba.py` — Alibaba Cloud Provider (ECS)
`alibabacloud-ecs20140526`. `DescribeInstances`, `StartInstance`, `StopInstance`.

### `skydash/providers/registry.py` — Provider Registry
Maps provider keys → provider instances. `get_provider(key)`.

### `skydash/templates/base.html` — Base Template
Shared layout: dark gradient background (`#1a1a2e` → `#0f3460`), navbar with
logo/site name, user info, logout/admin buttons, flash messages, footer,
toast notification, loader modal. All templates extend this.

### `skydash/templates/index.html` — Dashboard
Card grid with search, filter by provider/status, sort by name/provider/status/
region. JavaScript polls `/api/statuses` every 30s, updates badges and IPs.
Action buttons with multi-stage progress (loader modal + toast).

### `skydash/templates/detail.html` — Instance Details
Overview, Hardware, Network, Actions cards. Logs section with tabs
(ALL/INFO/WARNINGS/ERRORS) and scan buttons. Hermes Agent section with
SSH log retrieval, disk status, test connection. Live status polling.

### `skydash/templates/admin.html` — Admin Panel
3 tabs: 🌍 Site Settings (name, description, favicon, logo), 👤 Profile
(username, email, change password), 🖥️ Instances (hide/show, add/edit/remove
custom instances). Edit modal for display_name, description, tags.

### `skydash/templates/login.html` — Login Page
Stylish standalone login page with dark gradient background, branded card,
username/password form, error display.

### `skydash/templates/404.html` — 404 Error Page
Extends base.html, centered card with emoji 🔍, 404 message, button to dashboard.

### `skydash/templates/503.html` — 503 Error Page
Extends base.html, centered card with emoji 🔧, 503 message, retry button.

---

## 5. Architecture Diagram (data flow)

```
  terraform.tfstate                    Cloud APIs (AWS/Azure/Oracle/Alibaba)
        |                                          |
        v                                          |
  state_reader.py                                   |
   get_instances() -> list[Instance]                |
        |                ^                          |
        |    _apply_overrides()                     |
        |     (config_store)                        |
        v                                           v
     app.py ---- provider.registry ---- providers/*.py
     (Flask)     get_provider(key)       (boto3 / azure / oci / alibaba)
        |            |                                |
        |    config_store.py                          |
        |     (skydash_config.json)                   |
        v                                           v
   templates/                              live status + start/stop
   (base.html / index.html / detail.html   + IPs (refreshed live)
     / admin.html / 404.html / 503.html)
```

**Static data** (name, type, region, IPs, tags) flows: TF state -> state_reader ->
Instance model -> _apply_overrides (config_store) -> template.
**Live data** (power state, current IPs) flows: Cloud API -> provider ->
`_live_status()` cache -> `/api/statuses` JSON -> JavaScript updates the DOM.

---

## 6. How to Run / Restart

```bash
cd ~/skydash
source venv/bin/activate

# Install/update dependencies from pinned requirements.txt
pip install -r requirements.txt

# Stop the running instance (bracket trick avoids matching this command itself)
pkill -f '[a]pp.py'

# Load cloud credentials from .env
set -a
source ~/terraform/.env
set +a

# Start in background
nohup venv/bin/python app.py > flask.log 2>&1 &
```

The app runs on **http://0.0.0.0:8080**.
Flask auto-starts after reboot via **crontab** (loads `~/terraform/.env`).

> **Credentials** are in `~/terraform/.env` (`AWS_*`, `ARM_*`, `ALICLOUD_*`, `OCI_*`).
> **Never modify `.env` without user permission.**

---

## 7. Task Tracking — TODO / IN PROGRESS / DONE

> **This section is the project memory. Update it every time a task is started,
> completed, or blocked. When you lose context, read this section first.**
> **CRITICAL RULE: After each sub-step of the main prompt, update the status
> (TODO → IN PROGRESS → DONE) in this table immediately.**

### DONE

| # | Task | Date | Notes |
|---|------|------|-------|
| 1 | Terraform IaC for 4 clouds, 7 instances | 2026-07-28 | All imported into state |
| 2 | Provider-independent architecture (base.py + registry) | 2026-07-29 | See SPEC.md |
| 3 | Flask dashboard with cards (index.html) | 2026-07-29 | Search/filter/sort + auto-refresh |
| 4 | Instance details page (detail.html) | 2026-07-29 | Overview/Hardware/Network/Actions |
| 5 | Start/Stop for all 4 providers | 2026-07-29 | boto3 / azure / oci / alibaba SDKs |
| 6 | Live status polling (AJAX, 30s) | 2026-07-29 | `/api/statuses` endpoint |
| 7 | Azure power state fix (was "unknown") | 2026-07-29 | Read from VM instance view |
| 8 | Bootstrap JS load order fix | 2026-07-29 | Moved to `<head>` |
| 9 | Can-manage button fix | 2026-07-29 | `can_manage = available()` |
| 10 | Environment variable loading fix | 2026-07-29 | `set -a` before sourcing `.env` |
| 11 | IP change fix (dashboard refreshes IPs live) | 2026-07-30 | `fetchStatuses()` updates IP elements |
| 12 | Log tabs on detail page (ALL/INFO/WARN/ERROR) | 2026-07-30 | `/logs/<slug>` endpoint + `get_logs()` |
| 13 | Loader modal for actions | 2026-07-30 | Bootstrap modal + spinner |
| 14 | Comprehensive project documentation (this README) | 2026-07-30 | Full memory file for AI assistants |
| 15 | Instance-type specs lookup (CPU/RAM for AWS/Azure) | 2026-07-30 | `instance_specs.py` fills state gaps |
| 16 | Multi-stage action notifications | 2026-07-30 | Detailed progress for start/stop/refresh |
| 17 | Smart logs section (scan buttons) | 2026-07-30 | Scan for errors/warnings + refresh |
| 18 | Fix "Loading..." never ends on detail page | 2026-07-30 | Proper error handling in refreshStatus() |
| 19 | Fix `request` not imported in app.py | 2026-07-30 | Was causing 500 on /logs endpoint |
| 20 | Fix IP update logic (data attributes) | 2026-07-30 | Robust IP targeting in fetchStatuses() |
| 21 | **Fix "Loading..." stuck on dashboard** (critical) | 2026-07-30 | Loader modal HTML was AFTER `</script>` → JS crash |
| 22 | **Fix Hermes live IP** (stale TF state IP) | 2026-07-30 | AWS provider fetches live IP from API |
| 23 | **Authentication & Login Page** | 2026-07-30 | Session-based auth, werkzeug.security, login_required |
| 24 | **Hermes Agent SSH log retrieval** | 2026-07-30 | paramiko-based: Gateway, Signal, Commands logs |
| 25 | **Disk status monitoring** | 2026-07-30 | SSH df -h parsing, directory usage, inode usage |
| 26 | **Client caching + parallel fetch** | 2026-07-30 | Cached SDK clients; ThreadPoolExecutor (7 threads) |
| 27 | **UI Refactor (base.html, emoji, dark gradient)** | 2026-07-31 | All templates extend base.html, emoji-friendly |
| 28 | **Admin Panel (site settings, profile, password)** | 2026-07-31 | config_store.py, admin.html with 3 tabs |
| 29 | **Error pages (404, 503)** | 2026-07-31 | 404.html, 503.html with error handlers in app.py |
| 30 | **Instance management (hide/show, add/remove)** | 2026-07-31 | admin.html instances tab, hide/unhide/add/remove routes |
| 31 | **Edit Instance feature** | 2026-07-31 | ✏️ Edit button, modal with display_name/description/tags |
| 32 | **Documentation consolidation** | 2026-07-31 | Context Checkpoint, priority TODO, merged reports |
| 33 | **SSH key configured for Hermes Agent** | 2026-07-31 | Ed25519 key, authorized_keys added, .env configured |
| 34 | **CI/CD review & hardening** | 2026-08-01 | Reviewed deploy.yml, generated requirements.txt |
| 35 | **requirements.txt with pinned deps** | 2026-08-01 | Direct deps pinned; pip dry-run verified |
| 36 | **Pre-deploy syntax validation in CI/CD** | 2026-08-01 | py_compile gate before rsync; fails fast on syntax errors |
| 37 | **Crontab double-start fix** | 2026-08-01 | Removed duplicate @reboot entry that caused "Address already in use" |

### 🔴 URGENT

*No urgent tasks at this time.*

### 🟠 HIGH

| # | Task | Expected Date | Notes |
|---|------|---------------|-------|
| 1 | Set secure admin password | TBD | Add SKYDASH_ADMIN_PASSWORD to ~/terraform/.env |

### 🟡 MEDIUM

| # | Task | Expected Date | Notes |
|---|------|---------------|-------|
| 1 | Test Hermes Agent SSH connection | TBD | Click "Test Connection" on detail page |
| 2 | Test Admin Panel features | TBD | Add/Edit/Remove instances, change site name |

### 🟢 NORMAL

| # | Task | Date | Notes |
|---|------|------|-------|
| 1 | Real server logs (not mock) | Future | SSH access to each instance |
| 2 | Dark/Light theme toggle | Future | CSS variable-based theming |
| 3 | Instance uptime display | Future | Start time tracking |
| 4 | Reboot action | Future | Add reboot to all providers |
| 5 | SSH shortcut buttons | Future | Direct SSH from dashboard |
| 6 | Bulk actions (select all) | Future | Multi-select instances |
| 7 | Export/import config | Future | Backup/restore skydash_config.json |
| 8 | Webhook notifications | Future | Alert on status changes |
| 9 | Multi-user authentication | Future | Currently single-user |
| 10 | Production hardening | Future | HTTPS, rate limiting, CSRF |

---

## 8. Known Limitations

- **Auth password**: Default is `admin` (set via `SKYDASH_ADMIN_PASSWORD` env var).
  Add `SKYDASH_ADMIN_PASSWORD=your_password` to `~/terraform/.env` to customize.
- **Hermes Agent SSH**: Requires SSH key-based auth. Set `HERMES_SSH_KEY_PATH`,
  `HERMES_SSH_USER`, `HERMES_SSH_HOST` in `.env`. The public key must be added to
  the Hermes server's `~/.ssh/authorized_keys`. Without it, Hermes Agent buttons
  will show "SSH key not found" errors.
- **OS/RAM for AWS**: Terraform state doesn't persist these. Filled from
  `instance_specs.py` lookup table when available, otherwise shown as `—`.
- **CPU/RAM for Azure**: Same — filled from specs lookup.
- **Logs**: Currently generated as smart mock data (instance activity, status
  history, provider errors). Real server logs would require SSH access to each
  instance.
- **Status cache**: 60-second TTL — there may be a brief delay between an action
  and the status reflecting it. Auto-refresh polls every 30s (hits cache).

---

## 9. Instructions for AI Assistants (Cline / Hermes)

### Before starting any task:
1. **Read this README.md first** — it is the project memory.
2. **Read `REQUIREMENTS.md`** for behavioral rules.
3. **Read `SPEC.md`** for feature goals.
4. **Read `PROMPT_LOGGING.md`** for logging requirements.
5. **Read the latest session summary** in `skydash/docs/` (if exists).
6. **Read Section 2 (Context Checkpoint)** for current activity status.
7. **Read the latest log** in `Documentation/logs/`.

### Language rules (from REQUIREMENTS.md):
- **Documentation, logs, code comments**: English
- **Communication with the user**: Ukrainian

### During a task:
After each sub-step of the main prompt, **update the TODO / IN PROGRESS / DONE
table** (Section 7) immediately. This ensures that:
- If the session is interrupted, the next assistant knows exactly what was done.
- The project memory stays accurate and up-to-date.
- The status of each sub-task is clear at a glance.

### After completing any task:
1. **Update the TODO / IN PROGRESS / DONE table** (Section 7).
2. **Update Section 7 (Known Limitations)** if relevant.
3. **Update Section 2 (Context Checkpoint)** with current activity status.
4. **Write an execution log** in `Documentation/logs/` (per PROMPT_LOGGING.md).
5. **Update or create a session summary** in `skydash/docs/`.
6. **Verify functionality** — restart Flask, check logs, test requests.

### Safety rules:
- **Never modify `.env`** without explicit user permission.
- **Never perform destructive operations** (deleting files, modifying cloud
  resources, changing infrastructure) without user confirmation.
- If anything is unclear: **ask the user first.**

---

## 10. API Reference (22 routes)

### Auth (2)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/login` | Login page |
| POST | `/login` | Authenticate (username/password) |
| GET | `/logout` | Logout (clears session) |

### Dashboard & Instances (6)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard (requires auth) |
| GET | `/instance/<slug>` | Detail page (requires auth) |
| POST | `/instance/<slug>/start` | Start instance |
| POST | `/instance/<slug>/stop` | Stop instance |
| GET | `/api/statuses` | All instances status (parallel fetch) |
| GET | `/api/status/<slug>` | Single instance status |

### Admin Panel (8)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin` | Admin panel |
| POST | `/admin/settings` | Save site settings |
| POST | `/admin/profile` | Save admin profile |
| POST | `/admin/password` | Change admin password |
| GET | `/admin/instance/<slug>/hide` | Hide instance from dashboard |
| GET | `/admin/instance/<slug>/unhide` | Show instance on dashboard |
| POST | `/admin/instance/add` | Add custom instance |
| GET | `/admin/instance/<id>/remove` | Remove custom instance |
| GET | `/admin/instance/<slug>/edit` | Edit instance form (modal) |
| POST | `/admin/instance/<slug>/edit` | Save instance edit |

### Logs & Hermes Agent (6)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/logs/<slug>` | Cloud logs (?type=all|info|warning|error) |
| GET | `/logs/<slug>/scan` | Categorized log scan |
| GET | `/hermes/<slug>/logs/<type>` | Hermes SSH logs (gateway/signal/commands/all) |
| GET | `/hermes/<slug>/disk` | Hermes disk status |
| GET | `/hermes/<slug>/test` | Hermes SSH test & diagnostics |
| GET | `/refresh` | Clear status cache |

### Status values
`running` · `stopped` · `starting` · `stopping` · `error` · `unknown` · `loading`

---

## 11. Git & CI/CD

- **Repository**: https://github.com/DadjMahal/TerraSky (private)
- **CI/CD**: GitHub Actions auto-deploy on push to `main`
- **Workflow**: `.github/workflows/deploy.yml`
- **Deploy target**: 74.248.232.219 via SSH
- **Secrets**: `SSH_PRIVATE_KEY`, `SERVER_IP` (in GitHub repo settings)
- **Dependencies**: `skydash/requirements.txt` (pinned, pip-resolved transitive deps)
- **Pre-deploy gate**: `py_compile` syntax check on all Python files before rsync
- **Health check**: Fails CI if `/login` doesn't return HTTP 200 after restart

---

## 12. Task Planning (100 Tasks)

### Overview
For comprehensive task planning covering UI/UX, Agent integration, Logging, Cloudflare, Monitoring, Backup, and Port Management, see:

- **Master Index**: `skydash/docs/task_planning/100_tasks_master_index.md`
- **Task Files**: `skydash/docs/task_planning/`

### Quick Links by Category
1. **UI/UX Dashboard** (Tasks 1-10) → `01_ux_shutek_dashboard.md`
2. **UI/UX Detail Pages** (Tasks 11-20) → `02_ux_shutek_detail_pages.md`
3. **Hermes Agent** (Tasks 26-40) → `03_agent_hermes_integration.md`
4. **Cline Agent** (Tasks 27-41) → `04_agent_cline_integration.md`
5. **Error Logging** (Tasks 42-60) → `05_error_logging_system.md`
6. **Cloudflare Integration** (Tasks 61-72) → `06_cloudflare_integration.md`
7. **Live Monitoring** (Tasks 73-82) → `07_live_monitoring.md`
8. **Backup System** (Tasks 83-90) → `08_backup_system.md`
9. **Port Management** (Tasks 91-100) → `09_port_management.md`

### Status Legend
- **PLANNED**: Task identified, not started
- **IN_PROGRESS**: Currently being worked on
- **DONE**: Completed successfully
- **BLOCKED**: Pending required resources

---
