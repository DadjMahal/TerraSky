# 📊 STATUS — SkyDash current state (honest, verified)

> **Update after every milestone.** Only list what is **verified** (with evidence),
> never "claimed". Run `scripts/status.sh` to regenerate live status.

## 🔄 Service status (verified 2026-08-10)

> **Fresh DigitalOcean droplet deployment.** The agent was moved off the
> previous Azure-2 VPS (`74.248.232.219`, now unreachable) and redeployed on a
> new Ubuntu 24.04 droplet at `167.172.188.248`. The web stack (Flask + nginx +
> systemd) was re-created from this repo against the documented production layout
> `/home/volodro/{skydash,terraform,deploy/nginx,scripts}` using the
> `skydash.service` systemd unit.

```bash
$ systemctl is-active skydash.service        # active
$ ss -tlnp | grep -E ':80 |:8080 '
LISTEN 0  511 0.0.0.0:80    ... users:(("nginx"...))
LISTEN 0  128 0.0.0.0:8080  ... users:(("python","app.py",pid=5642))
$ curl -s -o /dev/null -w "%{http_code}\n" http://localhost/login          # 200
$ curl -s http://localhost/login | grep -o '<title>[^<]*</title>'          # <title>Sign in | SkyDash</title>
```
- ✅ **skydash.service active** (systemd), Flask on :8080
- ✅ **nginx reverse proxy** on :80 → 127.0.0.1:8080 (`deploy/nginx/skydash.conf`)
- ✅ **Public site live:** http://167.172.188.248/ — `/login` → HTTP 200,
  title `<title>Sign in | SkyDash</title>` (post-redesign title).
- ✅ **Login + dashboard end-to-end:** POST `/login` (admin/admin) → 302 → `/`
  (200, "Dashboard | SkyDash"); `/api/statuses` + `/api/load` → 200; static
  CSS/JS assets → 200. Verified against the public IP (UFW inactive, nginx on
  0.0.0.0:80).
- ✅ **CI/CD:** GitHub Actions `deploy.yml` (sync → nginx → systemd → health
  check). Note: that workflow SSHes in as `volodro@SERVER_IP`; on this fresh
  droplet the `volodro` user + deploy key must be configured for Actions to
  re-run (the unit file + nginx config are already installed locally).
- ✅ **Providers / SDKs:** All four provider SDKs (boto3, azure-mgmt-compute,
  oci, alibabacloud-ecs20140526) + Flask-SocketIO + paramiko are installed in
  `/home/volodro/skydash/venv` (70 packages). `available()` returns False until
  the matching `*_ACCESS_KEY`/`ARM_*`/`OCI_*`/`ALICLOUD_*` env vars are present
  in `terraform/.env` (see Known Limitations).

### ✅ Instance inventory — all live & running (verified 2026-08-10, post-AWS+OCI-activate)
User kept **AWS + DigitalOcean + Oracle**; Azure and Alibaba pruned. Vikunja
removed (only Hermes requested). All 5 remaining instances show live `running`
status with real IPs and `can_manage=true` (Start/Stop enabled):

| Instance | Provider | Status | Public IP | Cloud ID |
|----------|----------|--------|-----------|----------|
| aws-hermes | aws | `running` ✅ | 63.179.97.116 | i-01b445d2825c75ab9 |
| digital-1 | digitalocean | `running` ✅ | 207.154.201.40 | 591231372 |
| digital-2 | digitalocean | `running` ✅ | 167.172.188.248 | 591231377 |
| digital-3 | digitalocean | `running` ✅ | 167.71.32.118 | 591231381 |
| oracle-hunter | oracle | `running` ✅ | 92.5.22.94 | ocid1.instance.oc1.eu-frankfurt-1.…wecmnv2ja |

**DigitalOcean** — live. Token `DIGITALOCEAN_ACCESS_TOKEN` stored in the
git-ignored `terraform/.env` (chmod 600, volodro-owned). `seed_digitalocean_state.py`
enumerated your 3 live droplets via the DO API v2 and wrote real entries (valid
instance IDs, IPs) into state.

**AWS** — live. Credentials (`AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` +
`AWS_DEFAULT_REGION=eu-central-1`) stored in git-ignored `.env`. The Hermes
instance ID (`i-01b445d2825c75ab9`) was discovered by querying EC2 with
`describe-instances --filters "Name=tag:Name,Values=Hermes"` and written into
`terraform.tfstate`. `boto3` confirms `describe_instances` → state `running`, IP
`63.179.97.116`, `can_manage=true`.

**Oracle** — live. Credentials (`OCI_USER_OCID`, `OCI_TENANCY_OCID`,
`OCI_FINGERPRINT`, `OCI_PRIVATE_KEY_PATH`, `OCI_REGION=eu-frankfurt-1`) stored in
git-ignored `.env`. Private key PEM written to `/home/volodro/.oci/oci_api_key.pem`
(chmod 600). The Hunter instance (display_name `retry-bot-server`) was discovered
via `compute.list_instances` in eu-frankfurt-1; its OCID and compartment_id
written into state. `oci` SDK confirms `get_instance` → state `RUNNING`, live IP
`92.5.22.94`, `can_manage=true`.

## ✅ Done & verified (w/ evidence)

| Task | Evidence |
|------|----------|
| #1–3 Dashboard UI/UX (theme toggle, animations, fade-in) | Deployed; title check `Login &mdash; SkyDash` on :80 |
| #4–10 Dashboard UI/UX (Cat 1 complete) | `index.html` + `static/css/dashboard.css` + `static/js/dashboard.js` + `static/js/region-map.js`; new `/api/load` endpoint; verified `dash=200`, `/api/load` returns 7 rows, `/api/statuses` OK, all static assets HTTP 200 on test :8091 (2026-08-04); **DEPLOYED LIVE**: public `/api/load`→302 (route exists) + `/static/css/dashboard.css`→200 on 74.248.232.219 via GitHub Actions commit 6b08829 |
| #11–19 Detail pages (Cat 2 complete) | tabbed detail.html + `detail.css` + 6 JS modules (specs, timeline, metrics, topology, ssh-terminal, detail); backends `/api/metrics`, `/api/status-history`, `/api/domains`, Socket.IO `/ssh` (ssh_bridge.py); Flask-SocketIO in requirements + pip-install step in deploy.yml; verified on test :8093: detail=200, engine.io handshake OK, history recorded (2026-08-04); **DEPLOYED LIVE** commit 3e20e8d: public `/api/metrics`→302 (route exists) + Socket.IO handshake `{"sid":...}` on 74.248.232.219 |
| CI/CD pipeline fixed (nginx + systemd deploy) | GitHub Actions SUCCESS run 77c0f1f |
| 100-task planning docs | `skydash/docs/task_planning/*.md` + `TASKS.md` board |
| New doc framework | `START_HERE.md`, `AGENT_ONBOARDING.md`, `WORKFLOW.md`, `TASKS.md`, `STATUS.md`, `SESSION_HANDOFF.md` |

## ⚠️ In progress

| Task | Owner | Note |
|------|-------|------|
| **Full frontend redesign** (all templates + all CSS + visual layer of all JS) | Claude (Anthropic), 2026-08-05 | Built and reviewed **offline** — every template test-rendered via Jinja2 with dummy data (incl. edge cases: empty dashboard, admin edit modal, SSH tab), zero emoji remaining (scripted check), screenshotted via local headless render and manually reviewed. **NOT deployed, NOT click-tested against the live server** — no cloud creds / live instance data were available in that environment. See `skydash/docs/FRONTEND_HANDBOOK.md` § 8 "What is NOT verified" for the exact deploy+click-test checklist before this can move to "Done & verified". Two pre-existing bugs fixed in passing: dead `#ctx-start`/`#ctx-stop` refs in the context menu, missing `.hidden-by-page` CSS rule (pagination silently not hiding cards). |


## 🟠 Known limitations / open issues

1. **Azure / Oracle / Alibaba providers** may report `error` on status if their SDKs
   are not installed in the server venv (`azure-mgmt-compute`, `oci`,
   `alibabacloud-ecs20140526`). AWS works. Fix = ensure `requirements.txt` pip-installed
   in `/home/volodro/skydash/venv` on the server.
2. **Admin password** — `SKYDASH_ADMIN_PASSWORD` may not be set / weak default.
   Deferred to the **Backlog** in `TASKS.md` (security hardening, not feature work).
3. **Public IP may be behind a CDN/front proxy** — earlier the public :80 showed a
   stale nginx default before we configured reverse proxy; verify after CDN if present.
4. **`/` root returns 302 → /login** (auth) — expected, not a bug.

## 🔜 Next steps (highest impact first)

1. **Deploy + verify the frontend redesign** (see In Progress above and
   `skydash/docs/FRONTEND_HANDBOOK.md` § 8) — doesn't block the items below,
   but should happen before more UI work is layered on top of it.
2. Install cloud SDKs into server venv so all 4 providers report live status (prerequisite for many tasks).
3. Continue with **Category 3 — Hermes Agent** (#26 state widget, #27 SSH terminal, #28 remote exec…).
4. Then Category 5 logging.
   > "Set secure `SKYDASH_ADMIN_PASSWORD`" was moved to the **Backlog** in `TASKS.md` (security hardening).

## ⚙️ How to refresh this

```bash
cd /home/volodro && bash scripts/status.sh   # prints live state; use it as evidence
```
