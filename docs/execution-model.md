# SkyDash Execution Model

> **Created:** 2026-08-10 · Source: §38-41, §42, §65-68, §74-75 + current code.
> Current state: all work runs synchronously inside the Flask process.

## 1. Current Execution Flow

```
Browser → Flask app.py (routes) → provider.get_status()/start()/stop() (synchronous, thread pool)
                                → state_reader.get_instances() (tfstate parse)
                                → config_store (JSON)
```

- `/api/statuses` uses `ThreadPoolExecutor(max_workers=4)` — parallel status fetches (§84).
- No background jobs, no queue, no retry, no idempotency, no locking.

## 2. Target Execution Model

```text
API (Flask routes)
  │
  ├─ sync fast path (reads: status cache, inventory)
  └─ async ops (start/stop/deploy/terraform/backup)
        │
        ▼
   Queue (Redis/RQ or Celery)        §38 Job System
        │
        ▼
   Ephemeral Worker (isolated env)   §74 Worker Isolation
        │  - timeout  - audit  - output caps  - approval gate (prod)
        ▼
   Provider SDK / terraform CLI / ansible
        │
        ▼
   Job table: status, result, logs   §38-39
```

## 3. Key Mechanics

| Concern | Spec | Approach |
|---|---|---|
| Idempotency | §39 | operation_key = resource:action:sha1(params); unique index; no-op if running |
| Retry | §40 | exponential backoff (1s,2s,4s…max 5) for transient errors; idempotent-safe |
| Locks | §41 | Redis SET NX EX per resource during mutating op |
| Provider sync | §42 | periodic sync job → discover + update inventory + mark STALE |
| Approval | §66 | jobs carry required_approval; blocked until admin approves |
| GitOps | §65 | webhook → change → validate → plan → approval → apply → health |
| Command exec | §75 | never os.system from frontend; worker with allowlist + timeout + audit |

## 4. Terraform Execution (Iteration 5)

- Worker runs `terraform init/plan/apply` in an isolated dir (workspace per environment).
- Plan output parsed to machine-readable diff; prod destroy requires approval.
- Logs streamed to job log store (§103), state file encrypted (§13).