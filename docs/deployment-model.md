# SkyDash Deployment Model

> **Created:** 2026-08-10 · Source: §25-28, §60-61, §65-66. Current state: NOT implemented.

## 1. Application Model (§25)

```text
Application
   ├── id, name, project_id, repo_url, build_type (docker/zip/script)
   ├── Environments (dev/stage/prod)
   ├── Deployments (revision, status)
   └── Deployment strategies (blue-green, canary, rolling)
```

Currently no Application entity exists in the SkyDash domain model (`models.py` only has `Instance`).

## 2. Deployment Engine (§26)

API surface:
```text
POST /api/v1/applications/{id}/deployments
    { strategy: rolling, environment: production, ref: main }
GET  /api/v1/deployments/{id}
POST /api/v1/deployments/{id}/rollback
POST /api/v1/deployments/{id}/cancel
```

State: queued → validating → building → deploying → health_check → success | failed | rolled_back (§28).
Deployment record: id, app_id, env, strategy, commit, status, started/completed, logs_uri, initiated_by.

## 3. Pipeline Integration (§27)

```text
Git push → webhook (§61 GitHub/GitLab)
  → validate (branch/protection)
  → build artifact (worker isolation §74)
  → deploy to environment (staging → prod)
  → health check (SSH/systemd probe)
  → record audit trail (§37)
  → notify (§60)
```

## 4. Rollback (§28)

- Automatic rollback on failed health check (configurable).
- Rollback to last-known-good revision; audit event; notification.

## 5. GitOps (§65-66)

```text
Git → Change → Validation → Plan → Approval → Apply → Health check
```
- Production deploy/destroy requires approval (project admin) §66.
- This integrates with the Execution Model docs (`docs/execution-model.md`).

## 6. Current Readiness

- **Not implemented.** The existing `deploy.yml` GitHub Action only deploys SkyDash itself — not user applications.