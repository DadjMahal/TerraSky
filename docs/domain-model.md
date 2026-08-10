# SkyDash Domain Model — Multi-Cloud Infrastructure Management Framework

> **Created:** 2026-08-10 · Source: §2.4, §6, §127-128 of the spec + actual `models.py`.
> Current state: only `Instance` is implemented as a dataclass in `skydash/models.py`.

## 1. Entity-Relationship Overview (Target)

```text
Organization (1) ──< (N) Projects ──< (N) Environments ──< (N) Resources
      │                    │                    │               ├── Server
      │                    │                    │               ├── Network
      ├── Providers        ├── Teams            │               ├── Storage
      ├── Credentials      ├── Users            │               ├── Application
      ├── Audit            └── Budgets          │               └── Deployment
      └── Invoices                            ├── Costs
                                               ├── Secrets
                                               └── Infrastructure
```

## 2. Entities

### 2.1 Implemented today (`skydash/models.py`)

**Instance** (already implemented, dataclass):
| Field | Type | Notes |
|---|---|---|
| slug | str | URL-safe id, e.g. `aws-hermes` (no UUID — §128 gap) |
| name / display_name | str | resource name / human label |
| provider / provider_label | str | normalized key + label |
| instance_id | str | provider-native id (i-…, OCID, droplet id) |
| address | str | terraform address `type.name` |
| region / availability_zone | str | |
| instance_type | str | tf instance type |
| public_ip / private_ip / *_dns | str | live via provider |
| os / cpu / ram / disk_size | str | from specs table (`instance_specs.py`) |
| creation_date | str | |
| tags | dict | |
| status | str | STATUS_RUNNING/STOPPED/… |
| can_manage | bool | `provider.available()` |
| error | str | last error |
| extra | dict | compartment_id etc. |

### 2.2 Missing entities (to build in Iteration 0/1)

| Entity | Fields | Relationship |
|---|---|---|
| Organization | id, name, settings, created_at | 1:N Projects |
| Project | id, name, slug, org_id, tags, created_at | 1:N Environments, Teams |
| Environment | id, name, project_id, kind (dev/stage/prod), protection_reason | 1:N Resources |
| Resource | id, type, server/network/storage discriminator, status, owner | belongs to Environment |
| Server | instance_id, provider, ip, ssh_key, agent_enrolled | extends Resource |
| Credential | id, provider, scope, encrypted_blob, last_used, expires | 1:1 provider |
| User / Team | id, name, role (admin/owner/member) | N:N via memberships |
| Secret | id, key, value_encrypted, env_id, rotation_required | belongs to Env |
| Operation | id, type, resource_id, user_id, params, status, started, finished | action log |
| AuditLog | id, actor, action, resource, before/after, timestamp | append-only |
| CostRecord / Invoice / Budget | §51-55 | see billing-model.md |

## 3. Identity Strategy (§128 — UUIDs)

Migrate from slug-only to **UUID primary keys** with slugs retained as readable aliases:
```text
server: 9f8c7b3e-… (UUID)  | slug: aws-hermes (unique, URL-safe)
```

## 4. Storage (§127 — Database Core Entities)

Currently `config_store.py` persists to `skydash_config.json`. Target: PostgreSQL + SQLAlchemy with a migration system (Alembic), and tables for every entity above.
# Domain Model — SkyDash

> Maps the multi-cloud framework's entity model (§6 "Domain Model") to what
> exists in the current SkyDash codebase and what's missing.

## Current Implemented Entities

### `Instance` (§6.4–6.5) — IMPLEMENTED
**File:** `skydash/models.py:55-99`

```python
@dataclass
class Instance:
    slug: str           # stable URL slug, e.g. "aws-hermes"
    name: str           # canonical Terraform resource name ("Hermes")
    display_name: str   # provider-visible name
    provider: str       # normalized key (aws/azure/oracle/alibaba/digitalocean)
    provider_label: str # human-readable
    instance_id: str    # provider-native id (i-…, ocid1.instance…)
    address: str        # Terraform resource address

    # Static inventory (from terraform.tfstate)
    region, availability_zone, instance_type
    public_ip, private_ip, public_dns, private_dns
    os, cpu, ram, disk_size, creation_date, tags

    # Runtime state (filled live by provider implementations)
    status: str         # §43 Resource Status Model — IMPLEMENTED
    can_manage: bool
    error: str
    extra: dict         # provider-specific (e.g. resource_group_name for Azure)
```

**Status:** `STATUS_RUNNING, STATUS_STOPPED, STATUS_STARTING, STATUS_STOPPING, STATUS_ERROR, STATUS_UNKNOWN` (§43 — IMPLEMENTED in `models.py:39-45`)

**Mapped by:** `state_reader.py` — functions `_map_aws`, `_map_azure`, `_map_oracle`, `_map_alibaba`, `_map_digitalocean`

### `Provider` (§7) — PARTIALLY IMPLEMENTED
**File:** `providers/base.py:15-130` (CloudProvider ABC) + `providers/registry.py`

Abstract interface every cloud provider implements:
- `available()` → bool
- `get_status(instance)` → (status, error, public_ip, private_ip)
- `start_instance(instance)` → (bool, msg)
- `stop_instance(instance)` → (bool, msg)
- `get_logs(instance, type)` → list[str]  (default impl in base.py)
- `get_instance_details(instance)` → Instance

**Registered providers:** `registry.py:14-20` — aws, azure, oracle, alibaba, digitalocean

### `User` (§32) — PARTIALLY IMPLEMENTED
**File:** `auth.py` — single `admin` user, password via `config_store.py` (hash or env var `SKYDASH_ADMIN_PASSWORD`). No multi-user, no teams, no roles.

### `SiteSettings` (§47) — IMPLEMENTED
**File:** `config_store.py:17-28` — site name, description, favicon, logo, admin profile, hidden instances, custom instances, domain mappings.

## Missing Entities (per §6 hierarchy)

### Organization → Projects → Environments (§6.1) — NOT_IMPLEMENTED
No `Organization`, `Project`, or `Environment` entities exist. All instances are
flat. The spec requires:
```
Organization → Projects → Environments → {Infrastructure, Servers, Networks, Storage, Applications, Deployments, Costs/Invoices/Statistics}
```

### Providers (§6.1) — NOT_IMPLEMENTED
No `Provider` entity with metadata (account, regions, resources, usage, costs, sync, capabilities, health).
The current `registry.py` is an in-process registry, not a persistent entity.

### Credentials (§6.1) — NOT_IMPLEMENTED
Credentials live in `terraform/.env` (environment variables). No `Credential` entity
with created/last_used/expires/rotation_required (§69). No UI (§100).

### Users / Teams (§6.1) — NOT_IMPLEMENTED
No `Team` entity. Single admin user only. No RBAC (§33).

### Audit (§6.1) — NOT_IMPLEMENTED
No `AuditRecord` entity. No audit log.

### Resource Relationships (§88) — NOT_IMPLEMENTED
No `Relationship` entity. Resources are flat.

### Operation (§2.4) — NOT_IMPLEMENTED
No `Operation` entity. Every action is a direct API call, no event log or timeline (§87).

### Application (§6.1, §25) — NOT_IMPLEMENTED
No `Application` entity. No deployment engine (§26).

### Cost / Invoice / Usage (§6.1, §53) — NOT_IMPLEMENTED
No financial entities. `instance_specs.py` has static CPU/RAM/disk but no cost data.

### Policy (§6.1, §67) — NOT_IMPLEMENTED
No `Policy` entity. No policy engine.

### Secrets (§29-30) — NOT_IMPLEMENTED
No `Secret` entity. No secrets backend. Secrets in `.env` only (§124 — NOT_IMPLEMENTED).

### Metrics (§45) — PARTIALLY IMPLEMENTED
`hermes_agent.py` fetches disk status via SSH. `app.py` `/api/load` returns CPU/RAM. No `Metric` entity, no time-series storage.

### Alert (§46) — NOT_IMPLEMENTED

### Incident (§109) — NOT_IMPLEMENTED

## Proposed Entity-Relationship Diagram

```
Organization (1) ◄──┐
                    ├── (owns)
                   Project (M) ◄──┐
                                  ├── Environment (M) ◄──┐
                                  │                       ├── Server
                                  │                       ├── Network
                                  │                       ├── Storage
                                  │                       ├── Application
                                  │                       │   └── Deployment
                                  │                       ├── Secret
                                  │                       ├── Metric
                                  │                       ├── Alert
                                  │                       ├── Policy
                                  │                       └── Operation (log)
                                  ├── Cost
                                  ├── Invoice
                                  ├── Usage
                                  └── Budget
                                  │
                                  ├── Provider
                                  │   ├── Credential
                                  │   ├── Region
                                  │   └── Capability
                                  │
                                  └── Team
                                      └── User (M)


Relationships (§88): Resource → Network, Resource → Disk, Resource → Firewall,
Application → Deployment, Server → Network, Project → Cost, etc.

Dependencies (§89): Application depends_on Server, Server depends_on Network
```

## Implementation Priority (for Iteration planning)

| Priority | Entity | Reason |
|---|---|---|
| P0 | Project/Environment | §141 strategic workflow starts with "Create Project" |
| P0 | Credential | §100 credential UX is the import prerequisite |
| P1 | Secret | §29 required for secure deployments |
| P1 | AuditRecord | §37 required for compliance/security |
| P1 | Application/Deployment | §25-27 core value deliverable |
| P2 | Cost/Invoice/Budget | §51-55 financial management |
| P2 | Policy/Approval | §67-66 governance |
| P3 | Incident | §109 operational |
