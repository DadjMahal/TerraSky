# Terraform Integration — Design

> Covers §11–15 (Terraform/OpenTofu), §42 (sync), §102–104 (plan/apply UX),
> §106 (import), and the total integration scope.

## Current State

### State File — §11 — PARTIALLY IMPLEMENTED
**File:** `skydash/state_reader.py`

Reads `terraform.tfstate` (or `.tfstate.backup`) and parses:
- `resources[].instances[].attributes` for each resource type
- Maps `aws_instance`, `azurerm_linux_virtual_machine`, `oci_core_instance`,
  `alicloud_instance`, `digitalocean_droplet` → `Instance` model

```python
# state_reader.py: main entry
def read_state(state_path="terraform/terraform.tfstate") -> list[Instance]:
    # parses JSON, dispatches to _map_* per resource type
    # returns list of Instance objects (desired state inventory)
```

**Limitation:** tfstate is read once at app startup, not live-monitored.
No automatic refresh, no drift detection (§15).

### Terraform Files — §11
**Files:**
- `terraform/main.tf` — base infrastructure (VPC, security groups)
- `terraform/oracle.tf` — Oracle-specific resources
- `terraform/digitalocean.tf` — DO-specific resources
- `terraform/.env.example` — credential template

No `terraform plan`/`apply`/`destroy` execution in the app.
No `terraform import` (§106) — state is seeded by `scripts/seed_digitalocean_state.py`.

### Drift Detection — §15 — NOT_IMPLEMENTED
No comparison between tfstate (desired) and live provider state (actual).
The `_live_status` function in `app.py:90` gets live status but doesn't diff
against desired.

### Provider Sync — §42 — NOT_IMPLEMENTED
`state_reader.py` is invoked once at startup (not periodically).
`hermes_agent.py` periodically fetches disk status via SSH (§45) but this is
not connected to the Terraform state sync.

## Total Terraform Integration Scope (beyond current)

The current plan (§11) only reads tfstate. "Total integration" includes:

### Commands (§11.x)
| Command | Status | Notes |
|---|---|---|
| `terraform init` | NOT_IMPLEMENTED | Would need to run in worker |
| `terraform plan` | NOT_IMPLEMENTED | §102 — needs plan diff rendering |
| `terraform apply` | NOT_IMPLEMENTED | §102 — needs approval UX (§66) |
| `terraform destroy` | NOT_IMPLEMENTED | §102 |
| `terraform validate` | NOT_IMPLEMENTED | §11.x |
| `terraform fmt` | NOT_IMPLEMENTED | §11.x |
| `terraform import` | NOT_IMPLEMENTED | §106 |
| `terraform taint` / `untaint` | NOT_IMPLEMENTED | §11.x |
| `terraform state pull/mv` | NOT_IMPLEMENTED | §11.x |
| `terraform force-unlock` | NOT_IMPLEMENTED | §11.x |
| `terraform show -json` | PARTIALLY | §104 — state readable, but not live query |

### Backend (§13)
- **Current:** Local file `terraform/terraform.tfstate` only.
- **Total:** S3 remote backend, GCS remote backend, Terraform Cloud backend.
- **Security:** State file encryption at rest, versioning enabled,
  access policies (§13).
- **NOT_IMPLEMENTED** — requires infra: S3 bucket + DynamoDB lock table,
  IAM policies. REQUIRES_EXTERNAL_SERVICE for remote backends.

### Variables & Outputs
- **Variables:** `terraform.tfvars` handling, variable validation,
  workspace-specific variable files. NOT_IMPLEMENTED.
- **Outputs:** Parse `terraform.tfstate` outputs section. PARTIALLY
  (state_reader.py reads but doesn't expose outputs to UI).

### Modules (§11.x)
- Module registry integration, module versioning, module sources.
- NOT_IMPLEMENTED — terraform files are flat, no module sourcing.

### Workspaces (§12)
- `terraform workspace list/new/select/delete`.
- Workspace-to-environment mapping.
- NOT_IMPLEMENTED.

### Plan UX — §102–104
- Plan diff rendering (structured → human-readable).
- Execution logs streaming (§103).
- State inspection UI (§104).
- Approval gate (§66).
- NOT_IMPLEMENTED.

### Drift Detection — §15
- Scheduled `terraform plan` to detect drift.
- Drift alerting.
- NOT_IMPLEMENTED — REQUIRES_EXTERNAL_SERVICE (cron job or GitHub Actions scheduler).

### Policy Enforcement — §67-68
- OPA/Conftest policy-as-code gate on plans.
- Sentinel (Enterprise).
- NOT_IMPLEMENTED.

## Proposed Implementation Plan

### Iteration 5 (current scope — keep focused)
1. State reading ✓ (done)
2. Basic drift detection (compare tfstate vs live status)
3. tfvars variable support in state_reader
4. Simple plan output display (read, not execute)

### Total Integration (Expansion needed — §142)
To cover the full scope above, would expand to:
- Worker process (Celery/Redis) for command execution
- Remote backend support (S3 + Terraform Cloud)
- Plan diff rendering UI
- Approval workflow UX
- Policy engine (OPA) integration
- Scheduled drift detection (cron)
This is a **multi-iteration** effort, not feasible in Iteration 5 alone.
