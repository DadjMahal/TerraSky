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

## 🔧 Iteration 0 — Architecture Audit & Gap Analysis (COMPLETE)

**Completed 2026-08-10.** Mapped all 144 sections of
`Multi-Cloud Infrastructure Management Framework.md` to the actual codebase.
Created `docs/` directory with 8 design documents.

| File | § Covered | Lines | Status |
|------|-----------|-------|--------|
| `docs/architecture-gap-analysis.md` | §1–144 (all) | 223 | ✅ All 144 sections classified |
| `docs/domain-model.md` | §6, §25-31, §99 | 153 | ✅ Entity model mapped |
| `docs/provider-framework.md` | §7-10, §72-73, §83 | 157 | ✅ SDK design |
| `docs/security-model.md` | §29-41, §67-80, §105-108 | 113 | ✅ Risk register + roadmap |
| `docs/terraform-integration.md` | §11-15, §42, §102-104 | 121 | ✅ Current + total scope |
| `docs/api-reference.md` | §62, §94-95, §127 | 84 | ✅ Endpoints mapped |
| `docs/ui-wireframes.md` | §48-63, §86-87 | 100 | ✅ Tabs + gaps |
| `docs/infrastructure-diagram.md` | §3-4 | 100 | ✅ Topology + gaps |
| `docs/iteration-plan.md` | §134, §141 | 92 | ✅ 10 iterations mapped |

### Classification Summary (§144)
- **IMPLEMENTED:** 24 sections (17%)
- **PARTIALLY_IMPLEMENTED:** 28 sections (19%)
- **NOT_IMPLEMENTED:** 72 sections (50%)
- **REQUIRES_PROVIDER_SUPPORT:** 12 sections (8%)
- **REQUIRES_EXTERNAL_SERVICE:** 4 sections (3%)
- **IMPOSSIBLE_WITH_CURRENT_ARCHITECTURE:** 4 sections (3%)

### Knowledge Base Updated
- ✅ `START_HERE.md` — routing table updated with new docs/ entries; iteration workflow table added
- ✅ `STATUS.md` — this entry
- ✅ `TASKS.md` — new iteration-based task board added (old 100-task board archived as historical)
- ✅ `docs/` directory created with 8 design documents

### Key Finding: Terraform Integration Scope
**Current plan (Iter 5)** only covers tfstate reading + basic drift detection.
**"Total Terraform integration"** (all commands, remote backends, modules, OPA/Conftest,
Sentinel, CI/CD integration) is NOT in scope — it's a 3-iteration expansion
detailed in `docs/terraform-integration.md`. **Awaiting user decision** on whether
to expand Iter 5 or defer to later iterations.

## 🔜 Next steps (highest impact first)

**Iteration 1** was delivered alongside the Iter 0 audit as a security-hardening
baseline. All touched modules pass `python3 -m py_compile` (syntax verified);
**runtime/deploy verification is still pending** (Flask is not installed in this
environment and the production droplet has not been redeployed yet). See
`docs/architecture-gap-analysis.md` §3 for the root-cause analysis.

**Iteration 1 — in progress (code implemented in this pass):**
1. ✅ CSRF protection (Flask-WTF `CSRFProtect`) on all POST routes — hidden form
   tokens + AJAX `X-CSRFToken` fetch interceptor (`templates/*.html`,
   `static/js/csrf-header.js`, `app.py`). §77
2. ✅ Rate limiting (Flask-Limiter) on login + mutating admin routes (`auth.py`). §76
3. ✅ `/api/v1/` Blueprint + deprecation header on legacy `/api/`. §62
4. ✅ OpenAPI 3.0 spec + Swagger UI (`skydash/openapi.py`; `/api/v1/openapi.json`, `/api/v1/docs`). §§62,125
5. ⬜ Persist `app.secret_key` to env file instead of dev default. § Iter 1
> The old "Deploy + verify frontend redesign" task remains in progress — see
> `START_HERE.md` routing table for details.

## 🛡️ Iteration 8 — Security & Governance (delivered, runtime-tested)

Code + unit tests shipped (real runtime verification — no Flask needed):

| Module | § | Verified |
|---|---|---|
| `crypto.py` | §31 AES-256-GCM (PBKDF2, salt-in-token) | round-trip + wrong-key/tamper-reject test PASS |
| `rbac.py` | §33-34 admin/operator/readonly + 403 FORBIDDEN | hierarchy test PASS (escalation bug fixed in review) |
| `audit.py` | §37 append-only JSONL + SHA-256 chain | append/query/tamper-detection test PASS |
| `policy.py` | §67-68, §107 policies-as-data + `prod_shield` | deny/approve/dev tests PASS |
| `security_checklist.py` | §76-80 matrix via `GET /api/v1/security/checklist` | read-only endpoint wired |

Wiring: `@audited` + `@rbac.require_role(admin)` on mutating admin/instance routes; prod-shield on start/stop
(§107); CLI `--approve`; OpenAPI `# /security/checklist`. Tests: `python3 skydash/tests/test_governance.py`.
Flask-runtime + deploy verification still PENDING (no Flask here / no droplet redeploy).
See `docs/security-governance-iter8.md` for the BLOCKED matrix (Vault/MFA/PostgreSQL/OPA = Iter 10 or user decision).

## 🔁 Iteration 3 — Infrastructure Lifecycle (delivered, unit-tested)

| Module | § | Verified |
|---|---|---|
| `drift.py` | §15 desired-vs-live comparison | compare/detect/summarize tests PASS; `GET /api/v1/drift` (unavailable providers honestly report "unverifiable") |
| `dependencies.py` | §88 resource relationships via tags | graph/dependents/topology tests PASS; `GET /api/v1/topology` |
| `scheduler.py` | §91 in-process stdlib scheduler | debounce test PASS; opt-in via `SKYDASH_SCHEDULER=1` (refreshes status cache) |
| `import_engine.py` | §14/§106 idempotent read-only import | wired `/admin/import` (audited, admin-gated); config_store `readonly` flag |

Live drift sweep + import execution need cloud creds (deploy) — logic is unit-tested here.
Tests: `python3 skydash/tests/test_lifecycle.py` (5/5 PASS; import_engine guarded on werkzeug).

## ⚙️ How to refresh this

```bash
cd /home/volodro && bash scripts/status.sh   # prints live state; use it as evidence
```
