# 🤝 SESSION HANDOFF — Full SkyDash state & knowledge

> Read this to reach near-full context cheaply (~2–3k tokens), once per session.
> Live source: `START_HERE.md` (orient) + this file (depth) + `TASKS.md` (board).
> **Rewritten at the end of each significant session.**

## 1. Project (one line)

**SkyDash** — lightweight single-server web panel managing 7 VMs across
AWS/Azure/Oracle/Alibaba from one dashboard. Flask (:8080) behind nginx (:80),
systemd-managed, GitHub Actions CI/CD. Inventory from `terraform/terraform.tfstate`.

## 2. Honest current state (verified, not claimed)

- **Live:** http://74.248.232.219/ serves `Login &mdash; SkyDash` (HTTP 200 via nginx).
- **CI/CD:** GitHub Actions deploy works end-to-end (sync → nginx → systemd → health check).
- **Done so far:** Cat 1 (#1–10 Dashboard UI/UX) + **Cat 2 (#11–19 Detail pages: tabs,
  progress loader, specs gauges, network topology, status timeline, web SSH terminal
  via Socket.IO/paramiko, log viewer, metrics charts, domain mapping)** + CI/CD pipeline
  fix + 100-task planning.
- **Remaining:** 82 task-board items (Hermes/Cline agents, logging, Cloudflare,
  monitoring, backups, ports) — see `TASKS.md`. "Set secure admin password" moved to Backlog.

## 0. Current session (2026-08-13)

- **Enhanced Interactive Region Map (#4):** Upgraded the Leaflet.js region map from
  simple provider-coloured markers to a **futuristic animated map** with:
  - **Animated pulsing markers** — layered icons with a provider-coloured outer ring
    (`fm-ring`), a status-coloured beacon pulse (`fm-pulse`), and a sharp inner core
    (`fm-core`). Colors from `PROVIDER_COLOR` and `STATUS_COLOR` maps.
  - **Network topology connection lines** — dashed polylines between instances:
    - **Hub lines** (primary AWS/gateway → all others): cyan `#4FC8E8`, thicker,
      animating via `dashOffset` shifting in `requestAnimationFrame`.
    - **Mesh lines** (peer-to-peer): dimmer gray dashed lines, static.
  - **Rich popups** — click any marker for a full details card: provider dot,
    status badge, instance type, region, availability zone, public/private IPs,
    OS, tags, and a button linking to `/instance/{slug}`.
  - **Marker ↔ card highlight sync** — hovering a map marker highlights the matching
    `.card-col[data-slug]` on the dashboard with `.fm-card-highlight` glow.
  - **Auto-fit bounds** — map auto-zooms to show all markers with padding.
  - **Lifecycle API** — `refresh()`, `highlight(slugs)`, `destroy()` for clean
    re-rendering via `dashboard.js` toggle.
  - Files: `static/js/region-map.js`, `static/css/dashboard.css`,
    `templates/index.html`, `templates/base.html` (Leaflet CSS link added).

## 3. Architecture (how files fit together)

```
skydash/
├── app.py             # Flask: 20+ routes (dashboard, detail, API, admin, actions)
├── auth.py            # login/logout + login_required decorator
├── config_store.py    # persistent JSON config (site settings, profile, overrides)
├── state_reader.py    # reads terraform.tfstate -> Instance objects
├── models.py          # Instance, status constants
├── hermes_agent.py    # SSH agent for remote log/disk retrieval
├── providers/         # CloudProvider interface + aws/azure/oracle/alibaba impls
│   └── registry.py    # provider registry (business logic is provider-independent)
└── templates/         # Jinja2 (base, index, detail, admin, login, 404, 503)
deploy/nginx/skydash.conf   # nginx reverse proxy :80 -> :8080
docs/ (task_planning)       # 100 task breakdowns by category
```

**Key principle:** business logic is 100% provider-independent — Flask/state-reader
go through the provider registry, never importing a concrete SDK directly. SDKs are
lazy-imported inside provider methods to keep 1 GB RAM usage low.

## 4. Deployment / CI-CD (current, verified)

1. Push to `main` → GitHub Actions `deploy.yml`.
2. `rsync` `skydash/`, `terraform/`, `deploy/nginx/` to server `power-vm-2`.
3. Configure nginx: install `skydash.conf` into sites-enabled, remove default, `nginx -t` + reload.
4. `systemctl restart skydash.service` (Flask on :8080, `EnvironmentFile=terraform/.env`).
5. Health check: HTTP 200 + title contains "SkyDash" on :80; then external check.
- Server SSH deployment key: `~/.ssh/github_deploy` (CI uses `secrets.SSH_PRIVATE_KEY`).
- Deploy target hostname is `power-vm-2` (public 74.248.232.219; my sandbox is `free-vm`).

## 5. Known pitfalls / lessons (avoid repeating)

1. **`webfactory/ssh-agent` has NO `script:` input** — `script:` blocks are silently
   ignored. Always use `run:` + explicit `ssh -i ~/.ssh/deploy_key ...` for remote steps.
2. **`pkill -f "app.py"` self-match** — matches its own command line and kills the SSH
   session. Use the `[a]pp.py` bracket trick.
3. **Inline backgrounding via SSH hangs** — use systemd (`systemctl restart`), never
   `setsid nohup ... &` inside an SSH run step.
4. **rsync doesn't create destination dirs** — `mkdir -p` the remote target first.
5. **gitignore whitelist** — root `.gitignore` ignores everything except whitelisted
   dirs (`!skydash/`, `!terraform/`, `!deploy/`, `!Documentation/`, etc.). Add new
   artifact dirs there or they won't commit.
6. **Cloud SDKs must be installed in the server venv** — else Azure/Oracle/Alibaba
   providers report `error` on status. Ensure `requirements.txt` is pip-installed.

## 6. Key file/command map

- Orient: `START_HERE.md` · Rules: `AGENT_ONBOARDING.md` · Workflow: `Documentation/WORKFLOW.md`
- Board: `TASKS.md` · Status: `STATUS.md`
- Logs: `Documentation/logs/YYYY-MM-DD_<task>.md`
- Scripts: `scripts/session_start.sh` (resume-aware) · `scripts/session_end.sh` (commit+cleanup)
  · `scripts/status.sh` (live state)
- Live stack: `systemctl status skydash` · nginx `/etc/nginx/sites-enabled/skydash.conf`
- Server: SSH `ssh -i ~/.ssh/github_deploy volodro@74.248.232.219` (host `power-vm-2`)

## 7. Next recommended path

1. Install missing cloud SDKs in server venv (fixes live status for all 4 providers).
2. **Category 3 — Hermes Agent** (#26 state widget, #27 SSH terminal, #28 remote exec…).
3. Then Category 5 (logging).
   > "Set secure admin password" was moved to the Backlog in `TASKS.md`.
