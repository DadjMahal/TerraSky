# SkyDash Security & Governance — Iteration 8 (audit, RBAC, policies, crypto)

> **Status:** Code delivered + **runtime-tested** (no Flask needed — pure stdlib/cryptography).
> Tests: `skydash/tests/test_governance.py` (`python3 tests/test_governance.py` → 4/4 PASS).
> Runtime **Flask/wiring** verification still pending (Flask not installed here; deploy required).

## What shipped (all compile + unit-verified)

| Module | § | What it does | Verified by |
|---|---|---|---|
| `skydash/crypto.py` | §31 | AES-256-GCM seal/unseal (PBKDF2-HMAC-SHA256, salt-in-token), graceful no-cryptography ImportError | round-trip + wrong-key/tamper rejection tests (real `cryptography 41.0.7`) |
| `skydash/rbac.py` | §33-34 | `admin>operator>readonly` hierarchy, `require_role` / `require_permission` → 403 `FORBIDDEN` envelope | hierarchy unit tests (incl. no-escalation fix) |
| `skydash/audit.py` | §37 | Append-only JSONL audit with SHA-256 hash chain, `@audited` decorator, `query()`, `verify_chain()` | append/query/tamper-detection test |
| `skydash/policy.py` | §67-68, §107 | Policies-as-data evaluator + `prod_shield()` (deny destructive ops on prod tags unless approved) | deny/approve/dev/read tests |
| `skydash/security_checklist.py` | §76-80 | Hand-maintained governance matrix, served read-only | `GET /api/v1/security/checklist` |

**Wiring (app.py):** all mutating admin + instance-action routes got `@audited(...)`; admin routes got
`@rbac.require_role(rbac.ADMIN)` (single-profile default = `admin`, so existing behavior is unchanged);
start/stop paths are prod-shielded (§107) — stopping a `env=prod`-tagged instance now 403s without an
`approval` token (`prod:<slug>` or the slug itself) and records an audit denial; CLI `start`/`stop` gain
`--approve`. OpenAPI spec gained `/security/checklist`.

## Fixed during review
- **RBAC escalation bug** (`rbac.role_can`): hierarchy branch used `>= mine`, letting `readonly` inherit
  `operator` permissions (e.g. `server.stop`). Corrected to `< mine` (roles inherit from strictly-less-privileged
  roles). Regression-covered by `test_rbac_role_hierarchy`.

## BLOCKED (external services / future iterations — required to fully close the §)
| Item | § | Required for | Requires |
|---|---|---|---|
| Vault/KMS secret backend | §29-30 | replace env-file secrets | external service (Iter 10) |
| Multi-tenancy / org-project isolation | §35-36 | real row-level isolation | PostgreSQL domain model (Iter 10) |
| MFA (TOTP) | §68 | approve destructive without manual convention | user store (Iter 10) |
| OPA/Conftest engine | §67 pool | declarative policy bundles | `opa`/`conftest` binary |
| Audit table + full retention | §37, §122 | DB-backed searchable audit | PostgreSQL (Iter 10) |
| Per-user RBAC store | §33 | multi-user roles | users table (Iter 10) |
| GDPR delete workflows | §123 | right-to-delete | DB + key-management (Iter 10) |

**Convention notes:** `SKYDASH_SECRETS_KEY` must be set in the git-ignored env file for `crypto.py`;
audit JSONL lives in `skydash/audit_logs/` (already `.gitignore`d).