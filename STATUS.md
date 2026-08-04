# 📊 STATUS — SkyDash current state (honest, verified)

> **Update after every milestone.** Only list what is **verified** (with evidence),
> never "claimed". Run `scripts/status.sh` to regenerate live status.

## 🔄 Service status (verified 2026-08-04)

```bash
$ systemctl is-active skydash.service
active

$ ss -tlnp | grep -E ':80 |:8080 '
LISTEN  0  511  0.0.0.0:80   ...  users:(("nginx"...))
LISTEN  0  128  0.0.0.0:8080 ...  users:(("python", pid=...,"app.py"))
```
- ✅ **skydash.service active** (systemd), Flask on :8080
- ✅ **nginx reverse proxy** on :80 → 127.0.0.1:8080 (`deploy/nginx/skydash.conf`)
- ✅ **Public site live:** http://74.248.232.219/ — `/login` → HTTP 200,
  title `<title>Login &mdash; SkyDash</title>`
- ✅ **CI/CD:** GitHub Actions "Deploy SkyDash to Production" — last run SUCCESS
  (sync + configure nginx + systemd restart + health check)
- ✅ **Providers** (per instance): AWS OK; Azure/Oracle/Alibaba need SDKs present
  in the deployment venv — see Known Limitations below.

## ✅ Done & verified (w/ evidence)

| Task | Evidence |
|------|----------|
| #1–3 Dashboard UI/UX (theme toggle, animations, fade-in) | Deployed; title check `Login &mdash; SkyDash` on :80 |
| CI/CD pipeline fixed (nginx + systemd deploy) | GitHub Actions SUCCESS run 77c0f1f |
| 100-task planning docs | `skydash/docs/task_planning/*.md` + `TASKS.md` board |
| New doc framework | `START_HERE.md`, `AGENT_ONBOARDING.md`, `WORKFLOW.md`, `TASKS.md`, `STATUS.md`, `SESSION_HANDOFF.md` |

## ⚠️ In progress

| Task | Owner | Note |
|------|-------|------|
| — | | none right now |

## 🟠 Known limitations / open issues

1. **Azure / Oracle / Alibaba providers** may report `error` on status if their SDKs
   are not installed in the server venv (`azure-mgmt-compute`, `oci`,
   `alibabacloud-ecs20140526`). AWS works. Fix = ensure `requirements.txt` pip-installed
   in `/home/volodro/skydash/venv` on the server.
2. **Admin password** — `SKYDASH_ADMIN_PASSWORD` may not be set / weak default.
   Should be set securely (task).
3. **Public IP may be behind a CDN/front proxy** — earlier the public :80 showed a
   stale nginx default before we configured reverse proxy; verify after CDN if present.
4. **`/` root returns 302 → /login** (auth) — expected, not a bug.

## 🔜 Next steps (highest impact first)

1. Install cloud SDKs into server venv so all 4 providers report live status (#12 in the 
   "server statuses" recovery log; prerequisite for many tasks).
2. Set a secure `SKYDASH_ADMIN_PASSWORD`.
3. Continue UI/UX tasks: #4 interactive region map, #5 enhanced filters.
4. Then Category 3 Hermes agent (SSH/file mgmt) & Category 5 logging.

## ⚙️ How to refresh this

```bash
cd /home/volodro && bash scripts/status.sh   # prints live state; use it as evidence
```
