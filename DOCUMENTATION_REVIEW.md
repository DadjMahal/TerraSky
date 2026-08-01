# SkyDash Project Review & Comprehensive TODO List (33 Tasks)

## Project Overview

**SkyDash** — A lightweight web panel for managing cloud VMs across 4 providers (AWS, Azure, Oracle, Alibaba) with 7 monitored instances.

### Architecture
- **Frontend**: Single-page Flask app with Bootstrap 5, emoji-friendly UI
- **Backend**: Provider-independent architecture, SQLAlchemy models
- **Cloud Integration**: boto3 (AWS), azure-mgmt-compute (Azure), oci (Oracle), ECS SDK (Alibaba)
- **SSH Access**: Paramiko-based Hermes Agent log retrieval
- **Data Flow**: Terraform state (static) → Real-time API (dynamic)

---

## Priority-Based TODO List (33 Tasks)

### ✅ DONE — ✅ COMPLETED TASKS

| # | Task | Date | Notes |
|---|------|------|-------|
| 1 | Terraform IaC for 4 clouds, 7 instances | 2026-07-28 | All imported into state |
| 2 | Provider-independent architecture | 2026-07-29 | base.py + registry |
| 3 | Flask dashboard with cards (index.html) | 2026-07-29 | Search/filter/sort + auto-refresh |
| 4 | Instance details page (detail.html) | 2026-07-29 | Overview/Hardware/Network/Actions |
| 5 | Start/Stop for all 4 providers | 2026-07-29 | boto3 / azure / oci / alibaba |
| 6 | Live status polling (AJAX, 30s) | 2026-07-29 | /api/statuses endpoint |
| 7 | Azure power state fix | 2026-07-29 | Read from VM instance view |
| 8 | Bootstrap JS load order fix | 2026-07-29 | Moved to <head> |
| 9 | Can-manage button fix | 2026-07-29 | can_manage = available() |
| 10 | Environment variable loading fix | 2026-07-29 | set -a before sourcing .env |
| 11 | IP change fix (live update) | 2026-07-30 | fetchStatuses() updates IPs |
| 12 | Log tabs on detail page | 2026-07-30 | ALL/INFO/WARN/ERROR tabs |
| 13 | Loader modal for actions | 2026-07-30 | Bootstrap modal + spinner |
| 14 | Comprehensive project documentation | 2026-07-30 | Full README memory file |
| 15 | Instance-type specs lookup (CPU/RAM) | 2026-07-30 | instance_specs.py |
| 16 | Multi-stage action notifications | 2026-07-30 | Detailed progress for start/stop/refresh |
| 17 | Smart logs section (scan buttons) | 2026-07-30 | Scan for errors/warnings |
| 18 | Fix Loading stuck on detail page | 2026-07-30 | Proper error handling |
| 19 | Fix request import in app.py | 2026-07-30 | Was causing 500 on /logs |
| 20 | Fix IP update logic | 2026-07-30 | Robust data attributes |
| 21 | Fix Loading stuck on dashboard | 2026-07-30 | Loader modal BEFORE </script> |
| 22 | Fix Hermes live IP | 2026-07-30 | Live IP from API |
| 23 | Authentication system | 2026-07-30 | Session-based, werkzeug.security |
| 24 | Hermes Agent SSH log retrieval | 2026-07-30 | paramiko-based |
| 25 | Disk status monitoring | 2026-07-30 | df -h parsing + du + inodes |
| 26 | Client caching + parallel fetch | 2026-07-30 | Cached SDK clients, ThreadPoolExecutor |
| 27 | UI Refactor (base.html, emoji) | 2026-07-31 | All templates extend base.html |
| 28 | Admin Panel (settings, profile, password) | 2026-07-31 | config_store.py integration |
| 29 | Error pages (404, 503) | 2026-07-31 | Emoji-friendly error pages |
| 30 | Instance management | 2026-07-31 | hide/show, add/remove custom instances |
| 31 | Edit Instance feature | 2026-07-31 | display_name, description, tags |
| 32 | Documentation consolidation | 2026-07-31 | Context Checkpoint, priority TODO |
| 33 | SSH key configured for Hermes Agent | 2026-07-31 | Ed25519, tmux sessions, logs working |

### 🔴 URGENT — CRITICAL

| # | Task | Priority | Notes |
|---|------|----------|-------|
| - | **None currently** | | All urgent tasks complete! |

### 🟠 HIGH — IMPORTANT

| # | Task | Notes |
|---|------|-------|
| 1 | Set secure admin password | Add  to ~/terraform/.env |
| 2 | Install Hermes Agent binaries | Required if you need more detailed logs beyond what tmux outputs |

### 🟡 MEDIUM — SIGNIFICANT IMPROVEMENTS

| # | Task | Notes |
|---|------|-------|
| 1 | Test Hermes Agent fully | Click all buttons: Gateway Logs, Signal Logs, All Logs |
| 2 | Test Admin Panel features | Add/Edit/Remove instances, change site name/logo |
| 3 | Add Log scanning on detail page | Scan for errors/warnings in all logs |
| 4 | Add Hermes service status | Show if hdash and signal processes are running |

### 🟢 NORMAL — FUTURE ENHANCEMENTS

| # | Task | Notes |
|---|------|-------|
| 1 | Real server logs (SSH to instances) | Current logs are from tmux output |
| 2 | Dark/Light theme toggle | CSS variable-based theming |
| 3 | Instance uptime display | Track start time |
| 4 | Reboot action | Add reboot to all providers |
| 5 | SSH shortcut buttons | Direct SSH from dashboard |
| 6 | Bulk actions | Multi-select instances |
| 7 | Export/import config | Backup/restore skydash_config.json |
| 8 | Webhook notifications | Alert on status changes |
| 9 | Multi-user authentication | Currently single-user |
| 10 | HTTPS/TLS | Production security |
| 11 | Rate limiting | Prevent abuse |
| 12 | CSRF protection | Additional security |
| 13 | API key management | For automated access |
| 14 | Backup cron job | Auto-backup of skydash_config.json |
| 15 | User preferences | Theme, timezone, language |
| 16 | Instance search in admin | Filter instances |
| 17 | Instance tags display | Show tags on cards |
| 18 | Provider icons | Custom SVGs for AWS/Azure/Oracle/Alibaba |
| 19 | Cost calculator | Estimate monthly cost |
| 20 | Power consumption | Track kWh usage |
| 21 | Alert thresholds | Email/SMS on high CPU/disk |
| 22 | Action history | Log all start/stop events |
| 23 | Health check endpoints | /health for load balancers |
| 24 | JSON API for logs | Structured log endpoint |
| 25 | Mobile responsive improvements | Better on small screens |
| 26 | Performance analytics | Page load times, API latency |
| 27 | Service dependency map | Show instance relationships |
| 28 | Configuration templates | Pre-made skydash_config.json templates |
| 29 | Internationalization | Multi-language support |
| 30 | Unit tests | pytest coverage |
| 31 | Docker container | dockerize the app |
| 32 | CI/CD pipeline | GitHub Actions |
| 33 | Documentation translation | English/Ukrainian |
