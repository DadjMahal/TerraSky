# SkyDash GitOps & Deployment Design (§27, §65-66)

## Flow (target)

```text
Git push → webhook (GitHub/GitLab, §61)
  → validate (branch protection, commit signature)
  → plan (deterministic build command, dry-run)
  → approval gate if prod (§66 — skydash/deployments/approvals.py)
  → apply (skydash/deployments/applications.py run_deployment)
  → health check (systemd probe / HTTP 200)
  → audit (§37) + notify (§60)
```

## Current implementation (compile + unit verified)

| Piece | Module | Status |
|---|---|---|
| Application + DeploymentRecord model | `deployments/applications.py` | ✅ logic, dry-run runner |
| Deterministic deploy runner (timeout, output cap) | `deployments/applications.py:run_deployment` | ✅ |
| Rollback (re-run known-good) | `deployments/applications.py:rollback` | ✅ (dry-run) |
| Prod approval gate (pending→approved) | `deployments/approvals.py:gate/create/approve/deny` | ✅ unit-tested |
| Encrypted-at-rest secrets | `deployments/secrets.py` (AES-GCM via `crypto.py`) | ✅ unit-tested |
| API routes | `/api/v1/applications/*/deployments`, `/api/v1/secrets`, `/api/v1/approvals` | ✅ wired (py_compile) |

## BLOCKED (needs external infra / live host — documented, not faked)

- Real **build execution** on the production host (current runner is deterministic
  dry-run; `dry_run=False` is implemented but not live-run here).
- **Webhook receiver** — requires a public endpoint + GitHub/GitLab webhook secret
  (deployment infra).
- **Blue/green + canary routing**, **build farms**, **image registries**.
- Plan→apply diff rendering UI (§102-104) for user review.
- Notifications dispatch (SMTP/webhook) (§60).

## Approval conventions

- Non-prod deploy: zero-friction (no record created).
- Prod deploy / rollback / stop / terraform.apply / destroy: an approval record is
  created and the run stays `queued` until `POST /api/v1/approvals/<id>/approve`
  (admin-only). MFA (§68) for destructive approvals = Iteration 10.
