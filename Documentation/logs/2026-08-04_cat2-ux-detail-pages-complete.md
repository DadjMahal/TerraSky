# RuntimeLog — Category 2 UI/UX Detail Pages (#11–19) complete
**Date:** 2026-08-04
**Owner:** Cline

## Original prompt
"Each time finish task, deploy and start category 2." (User also specified: the destination
server 74.248.232.219 has 8GB RAM and is where software should be installed — I act as
LLMOps + developer; the sandbox is dev-only.)

## Objective
Complete all Category 2 UI/UX Detail-page tasks (#11 tabs, #12 progress loader,
#13 hardware specs viz, #14 network topology, #15 status timeline, #16 built-in SSH
terminal, #17 log viewer w/ highlight, #18 metrics charts, #19 custom domain mapping),
deploy after the milestone, and doc-sync.

## Backend (app.py + new modules)
- `status_history.py` (NEW) — JSON-persisted per-instance status transitions; recorded in
  `_live_status`; served by `/api/status-history/<slug>`  → #15.
- `/api/metrics/<slug>` — CPU/RAM/disk specs + (Hermes) live disk via hermes_agent → #18.
- `/api/domains` GET/POST/DELETE — custom domain→instance mapping persisted in
  config_store (`domain_mappings`) → #19.
- `ssh_bridge.py` (NEW) + Flask-SocketIO `/ssh` namespace — paramiko interactive channel
  bridged to xterm.js (`ssh_open`/`ssh_input`/`ssh_resize`/`ssh_output`/`ssh_status`)
  for the Hermes instance → #16.
- `app.run` → `socketio.run` when Flask-SocketIO present; `instance_detail` passes
  `socketio_available`.

## Frontend
- `templates/detail.html` — rewritten as tabbed interface (Overview, Hardware, Network,
  Actions, Timeline, Logs, Metrics, Domains, SSH-for-hermes).
- `static/css/detail.css` (NEW) — tabs, staged loader, gauges, topology, timeline,
  terminal, log viewer, charts, domain rows.
- `static/js/detail.js` (NEW) — status badge/refresh, staged action loader (#12), log
  loaders w/ level highlight (#17), domains CRUD (#19), lazy tab init.
- `static/js/specs-visualization.js` (#13 SVG gauges), `status-timeline.js` (#15),
  `metrics-charts.js` (#18 Chart.js), `topology.js` (#14 SVG), `ssh-terminal.js`
  (#16 xterm.js + socket.io-client).
- `base.html` — + detail.css.
- deploy.yml — added "Install / upgrade Python dependencies (server venv)" step so
  flask-socketio etc. install on the 8GB server; requirements.txt + Flask-SocketIO>=5.3,<6.
- config_store.py — added domain mapping functions, removed duplicated dead functions.

## Problems & solutions
1. **Flask-SocketIO pin conflict** — pinned python-socketio/engineio clashed; fixed by
   letting pip resolve (only `Flask-SocketIO>=5.3,<6`).
2. **Jinja `inst.to_dict()`** — `inst` is already a dict in detail.html; changed to
   `{{ inst|tojson }}`.
3. **Malformed detail.html after chunked inserts** — `{% block scripts %}` landed inside
   the SSH tab; rewrote the tail with correct structure.
4. **Port 8092/8093 in use by stale procs** — killed and used fresh ports for each test run.

## Verification (test :8093)
```
login=200  detail(hermes)=200  detail(azure)=200 (no ssh tab, correct)
tabs present: overview/hardware/network/actions/timeline/logs/metrics/domains/ssh  ✓
specs-host, timeline-host, metrics-host, topology-host, domain-form, ssh-host  ✓
/api/metrics/aws-hermes → {cpu,ram,disk} (+hermes disk attempt)  ✓
/api/status-history/aws-hermes → [{status:unknown,ts:...}] after polling  ✓
/api/domains POST→GET→DELETE round-trip OK  ✓
socket.io engine.io handshake → 0{"sid":...}  ✓
py_compile on app/config_store/status_history/ssh_bridge OK
```

## Deployment
Commit then `git push origin main` → GitHub Actions (new pip-install step) → verify public:
`/static/css/detail.css` 200, `/api/metrics/<slug>` route exists (302 unauth), Socket.IO handshake.

## Next steps
- Begin **Category 3 — Hermes Agent** (#26–40).
- Note: live CPU/RAM utilization (deeper #7/#18) still needs the Cat 7 monitoring agent.

## Remaining issues (echoed from prior logs)
- Azure/Oracle/Alibaba SDKs still need install in server venv (blocked live status).
- Admin password hardening remains in the Backlog.
- SSH terminal only enabled for the Hermes instance (SSH key via HERMES_SSH_KEY_PATH).
