# UI/UX Wireframes & Design — SkyDash

> Maps the framework's §48–63, §86–87 (UI/UX requirements) to the current
> templates and design system.

## Current Templates

**File listing:** `skydash/templates/`

| Template | § | Description |
|---|---|---|
| `login.html` | §32 | Login form with password field |
| `index.html` | §47 | Main dashboard — grid of server cards |
| `detail.html` | §49 | Per-server detail — tabs: Overview, Metrics, Terminal, Logs, Terraform |
| `base.html` | §86 | Layout: navbar + sidebar + content block |

## Static Assets

**`skydash/static/css/`**
| File | § | Description |
|---|---|---|
| `dashboard.css` | §47 | Grid layout, server cards, status colors |
| `terminal-full.css` | §19 | XTerm.js terminal styling |
| `login.css` | §32 | Login page styling |

**`skydash/static/js/`**
| File | § | Description |
|---|---|---|
| `dashboard.js` | §47 | Load instances, render cards, WebSocket status polling |
| `detail.js` | §49 | Detail page — tab switching, action buttons, SocketIO events |
| `ssh-terminal.js` | §19 | Full-screen SSH terminal via XTerm.js + SocketIO |
| `terraform.js` | §11 | Placeholder for Terraform action buttons |
| `metrics.js` | §45 | Chart.js CPU/RAM/disk metrics |

## Current UI State

### Dashboard (§47) — IMPLEMENTED
Server cards rendered from `/api/statuses` JSON. Each card shows:
- Server name, provider icon
- Status badge (green/yellow/red)
- Region, instance type
- Quick action buttons: Start, Stop, Details

### Server Detail (§49) — PARTIALLY IMPLEMENTED
Tabs implemented:
1. **Overview** — instance metadata (IP, region, type, etc.)
2. **Metrics** — CPU/RAM/disk charts via Chart.js
3. **Terminal** — SocketIO SSH terminal
4. **Logs** — system logs (dmesg, journalctl)
5. **Terraform** — placeholder only, no plan/apply diff

Tabs **NOT IMPLEMENTED** (§49 requires these per spec):
- **Files** (§20) — file browser/manager
- **Processes** (§21) — process list/kill
- **Services** (§22) — systemd/docker service management
- **Docker** (§23) — container management
- **Kubernetes** (§24) — cluster management

## Design System — FRONTEND_HANDBOOK.md (existing)

Per `START_HERE.md`, the current design system spec lives at:
`/home/volodro/skydash/skydash/docs/FRONTEND_HANDBOOK.md`

Key conventions from the handbook:
- Color tokens via CSS custom properties
- Status: `--status-running: #22c55e`, `--status-stopped: #f59e0b`, `--status-error: #ef4444`
- Grid: 12-column responsive with Tailwind-like utility classes
- Font: system UI stack, 16px base
- No framework components (no React/Vue) — vanilla JS + HTMX-style partials

## Gap vs. Spec (§86)

| § | Requirement | Status | Gap |
|---|---|---|---|
| §86 | Managed vs unmanaged distinction | NOT_IMPLEMENTED | All instances treated identically |
| §86 | Dangerous-action separation | NOT_IMPLEMENTED | Destroy/reboot same as start/stop UI |
| §86 | Danger zone confirmation | PARTIALLY | Delete has confirm dialog; no secondary confirmation |
| §86 | Action feedback (progress) | NOT_IMPLEMENTED | No progress indicators on API calls |
| §86 | Loading states | NOT_IMPLEMENTED | No skeleton loaders |
| §87 | Activity timeline | NOT_IMPLEMENTED | No timeline/event stream |
| §60 | Notification center | NOT_IMPLEMENTED | No toast/snackbar system |

## Proposed UI Iterations

### Iteration 1: Safety & Feedback
- Add CSRF tokens to all forms
- Add danger-zone separation for destroy/reboot
- Add toast notification system (§60)
- Add loading skeletons for metrics

### Iteration 2: Feature Tabs
- Implement Files tab (§20) — file browser via ssh_bridge
- Implement Processes tab (§21) — process list/kill
- Implement Services tab (§22) — systemd status/restart
- Implement Docker tab (§23) — container status/start/stop

### Iteration 3: Activity & Relationships
- Activity timeline (§87) — operation history per server
- Resource relationship graph (§88) — network/disk/firewall deps
- Inventory view (§57) — all resources across providers
