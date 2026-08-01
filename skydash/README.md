# SkyDash — Multi-Cloud Dashboard

Lightweight Flask web panel for managing cloud VMs across AWS, Azure, Oracle
Cloud, and Alibaba Cloud from a single dashboard.

## Quick Start

```bash
cd ~/skydash
source venv/bin/activate
set -a; source ~/terraform/.env; set +a
python app.py   # runs on http://0.0.0.0:8080
```

## Files

| File | Purpose |
|------|---------|
| `app.py` | Flask routes (22 routes), status cache, admin panel, error handlers |
| `auth.py` | Authentication module (login/logout/`@login_required`) |
| `config_store.py` | Persistent JSON config store (site settings, profile, overrides) |
| `hermes_agent.py` | SSH-based Hermes Agent log retrieval & disk monitoring |
| `models.py` | Provider-independent `Instance` dataclass |
| `instance_specs.py` | Instance-type → CPU/RAM lookup table |
| `state_reader.py` | Reads `terraform.tfstate` → `list[Instance]` |
| `providers/base.py` | Abstract `CloudProvider` interface |
| `providers/aws.py` | AWS (boto3) |
| `providers/azure.py` | Azure (azure-mgmt-compute) |
| `providers/oracle.py` | Oracle Cloud (oci SDK) |
| `providers/alibaba.py` | Alibaba Cloud (ECS SDK) |
| `providers/registry.py` | Provider key → instance mapping |

## Templates

| File | Purpose |
|------|---------|
| `templates/base.html` | Base layout (dark gradient, navbar, flash, toast, modal) |
| `templates/index.html` | Dashboard (card grid + auto-refresh) |
| `templates/detail.html` | Instance details + logs + Hermes Agent |
| `templates/login.html` | Login page |
| `templates/admin.html` | Admin panel (settings, profile, instances) |
| `templates/404.html` | 404 error page |
| `templates/503.html` | 503 error page |

## Docs

| File | Purpose |
|------|---------|
| `docs/session_summary_refactor_ui_admin.md` | Session handoff report (UI refactor + admin) |
| `docs/session_summary_2026-07-31.md` | Session summary (all features complete) |

See `../Documentation/README.md` for the full project memory and architecture.
