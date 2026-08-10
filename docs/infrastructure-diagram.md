# Infrastructure Diagram — SkyDash

> Maps the framework's §3–4 (Deployment Architecture) to the actual deployment.

## Live Deployment Topology (§4)

```
                    ┌─────────────────────────────────────────────┐
                    │              Internet (port 80)             │
                    └────────────────────┬────────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────────┐
                    │           nginx reverse proxy (:80)           │
                    │   - /static/ → /home/volodro/skydash/static/  │
                    │   - / → 127.0.0.1:8080                        │
                    │   - HTTPS redirect, gzip, rate-limit headers  │
                    │   - systemd: nginx.service                    │
                    └────────────────────┬────────────────────────┘
                                         │ 127.0.0.1:8080
                    ┌────────────────────▼────────────────────────┐
                    │         SkyDash Flask app (:8080)           │
                    │   - systemd: skydash.service                │
                    │   - venv: /home/volodro/skydash/venv        │
                    │   - Working dir: /home/volodro/skydash      │
                    └────────────────────┬────────────────────────┘
                                         │
           ┌─────────────────────────────┼─────────────────────────────┐
           │                             │                             │
           ▼                             ▼                             ▼
   ┌──────────────┐         ┌──────────────────┐        ┌──────────────────┐
   │  AWS EC2    │         │  Azure VM        │        │  Oracle VM       │
   │  (boto3)    │         │  (azure-mgmt)    │        │  (oci SDK)       │
   │  Port :22   │         │  Port :22        │        │  Port :22        │
   └──────┬──────┘         └────────┬─────────┘        └────────┬─────────┘
          │                         │                           │
          │                         │                           │
          ▼                         ▼                           ▼
   ┌──────────────┐         ┌──────────────────┐        ┌──────────────────┐
   │  Hermes VM  │         │  Hermes VM        │        │  Hermes VM       │
   │  (:22 via)  │         │  (:22 via)       │        │  (:22 via)      │
   │  SSH bridge  │         │  SSH bridge      │        │  SSH bridge     │
   └──────┬──────┘         └────────┬─────────┘        └────────┬─────────┘
          │                         │                           │
          ▼                         ▼                           ▼
   ┌──────────────┐         ┌──────────────────┐        ┌──────────────────┐
   │  DO Droplet │         │  Alibaba ECS    │        │                  │
   │  (DO SDK)   │         │  (alibabacloud) │        │  ...7 VMs total   │
   │  Port :22   │         │  Port :22       │        │                  │
   └─────────────┘         └─────────────────┘        └──────────────────┘

           ▲
           │
           │ File transfer / remote exec
           │ (paramiko SSH, hermes_agent.py)
           │
    ┌──────┴──────┐
    │  Config &   │
    │  State      │
    │  └── skydash_config.json  (runtime config, site settings)  │
    │  └── terraform.tfstate    (infrastructure inventory)      │
    │  └── terraform/.env        (provider credentials)          │
    └─────────────┘
```

## Single-Server Constraint (§4)

**Deployment host:** `volodro` — single Linux server (1 GB RAM, VPS).

- **No container orchestration** (§74 — Worker Isolation: NOT_IMPLEMENTED)
- **No background job queue** — all API calls are synchronous (§38: Job System NOT_IMPLEMENTED)
- **No separate worker process** for Terraform commands
- **In-process caching** only (§120): `app.py:71` `_STATUS_TTL=30s` dict cache
- **No PostgreSQL** — config persisted to `skydash_config.json` (§80: NOT_IMPLEMENTED)
- **No Redis** — no distributed cache, no session store
- **No Prometheus** — metrics in-memory only (§82: NOT_IMPLEMENTED)
- **No Grafana** — charts rendered client-side via Chart.js

## CI/CD (§4)

- **GitHub Actions** — `.github/workflows/deploy.yml`
  - Build → Test → Deploy to `volodro` server
  - Uses rsync + systemd restart
  - No staging environment (§107: Environment Protection NOT_IMPLEMENTED)
- **nginx config** — `deploy/nginx/skydash.conf`
  - Reverse proxy :80 → :8080
  - Static file serving
- **systemd units** — `skydash.service`
  - Auto-start on boot
  - Restart on failure

## What's Missing vs. §4

| §4 Requirement | Status | Gap |
|---|---|---|
| Queue / workers | NOT_IMPLEMENTED | Synchronous-only Flask |
| Horizontal scaling | IMPOSSIBLE | Single-process, in-memory cache |
| Ephemeral workers | NOT_IMPLEMENTED | No container runner for TF commands |
| Health checks | PARTIALLY | `/health` not defined; nginx health check only |
| Blue/green deploy | NOT_IMPLEMENTED | GH Actions does rolling restart only |
| Secrets in environment | PARTIALLY | `.env` file exists but no secret manager |
