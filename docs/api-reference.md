# API Reference — SkyDash

> Maps the framework's §62 (API) requirements to the actual REST+WebSocket API
> in `skydash/app.py`.

## Current API Surface

### REST Endpoints (§62) — PARTIALLY IMPLEMENTED

| Method | Route | § | Description | Auth |
|---|---|---|---|---|
| GET | `/login` | §32 | Login page (form) | open |
| POST | `/login` | §32 | Authenticate | open |
| GET | `/logout` | §32 | Logout | `login_required` |
| GET | `/` | §47 | Project/server dashboard | `login_required` |
| GET | `/project/<project_slug>` | §48 | Project view | `login_required` |
| GET | `/detail/<slug>` | §49 | Server detail page | `login_required` |
| GET | `/api/statuses` | §43 | All instance statuses | `login_required` |
| GET | `/api/load` | §45 | Live CPU/RAM metrics | `login_required` |
| GET | `/api/instances/<slug>/actions` | §16 | Available actions | `login_required` |
| POST | `/api/instances/<slug>/<action>` | §16 | Start/stop/reboot | `login_required` |
| GET | `/api/instances/<slug>/details` | §6 | Instance detail JSON | `login_required` |
| GET | `/api/instances/<slug>/metrics` | §45 | CPU/RAM/disk metrics | `login_required` |
| GET | `/api/instances/<slug>/logs/<type>` | §47 | System logs (dmesg, journal) | `login_required` |
| GET | `/api/instances/<slug>/health` | §44 | Health check | `login_required` |
| GET | `/api/settings` | §47 | Site settings | `login_required` |
| GET | `/api/providers` | §50 | Provider availability | `login_required` |
| POST | `/api/settings` | §47 | Update site settings | `login_required` |
| POST | `/api/instances/<slug>/customize` | §99 | Add custom instance | `login_required` |

### WebSocket Events (§127) — PARTIALLY IMPLEMENTED

| Namespace | Event | Direction | § | Description |
|---|---|---|---|---|
| `/ssh` | `connect` | C→S | §19 | Establish SSH WebSocket |
| `/ssh` | `ssh_command` | C→S | §19 | Send command to terminal |
| `/ssh` | `ssh_output` | S→C | §19 | Stream command output |
| `/ssh` | `ssh_disconnect` | C→S | §19 | Close SSH session |
| `/ssh` | `ssh_resize` | C→S | §19 | Resize terminal (cols/rows) |

No domain event WebSocket (e.g., `status_changed`, `operation_started`) —
only the SSH terminal uses WebSocket. §87 activity timeline and §101
notification system not implemented.

## Gap vs. Spec (§62)

| § Requirement | Status | Gap |
|---|---|---|
| /api/v1 versioning | NOT_IMPLEMENTED | No version prefix |
| OpenAPI spec | NOT_IMPLEMENTED | No `/api/openapi.json` or Swagger UI |
| Standardized error response | PARTIALLY | `app.py:149` returns `{"status":"error","error":msg}`; no error code enum |
| Pagination | NOT_IMPLEMENTED | No `?page=`/`?limit=` params |
| Filtering/sorting | NOT_IMPLEMENTED | No query-param-based filtering |
| Rate limiting | NOT_IMPLEMENTED | §76 |
| API tokens (§94) | NOT_IMPLEMENTED | Session-only auth |
| Service accounts (§95) | NOT_IMPLEMENTED | — |

## API Conventions

All endpoints return JSON:
```json
{ "status": "ok", "data": { ... } }
```
or on error:
```json
{ "status": "error", "error": "Human-readable message" }
```

## Proposed API Evolution

### Iteration 1: Foundation
- Add `/api/v1/` versioning prefix
- Generate OpenAPI 3.0 spec from route decorators
- Add `X-RateLimit` headers + `Flask-Limiter`
- Standardize error responses with codes (§113)

### Iteration 2: Tokens & Pagination
- Add API token auth (§94) — stateless JWT tokens
- Add pagination headers + `?page=1&limit=50` params
- Add `/api/v1/projects` (§48), `/api/v1/instances` list endpoint

### Iteration 3: Webhooks & Events
- Add domain event WebSocket (§127): `instance_status_changed`, `operation_completed`
- Add `/api/v1/webhooks` (§61) — outbound webhook dispatch on state changes
