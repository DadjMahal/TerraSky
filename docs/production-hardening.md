# SkyDash Production Hardening — Iteration 10 (design + DoD)

> **Status:** Design + testing delivered. **External services & live production
> deploy are BLOCKED on a user/owner decision** (budget for infra + drop access) —
> per `START_HERE.md` §87 and the repo's verify-before-claim rule, nothing here is
> marked "live" unless actually verified against the deployed system.

## What is already verifiable

- **§115 Testing strategy:** `scripts/run_tests.sh` runs 6 suites / 24 tests that
  need only stdlib + `cryptography` (no Flask): `test_governance`, `test_lifecycle`,
  `test_deployments`, `test_monitoring`, `test_agents`, `test_providers_contract`.
- **§116 Provider contract tests:** `tests/test_providers_contract.py` — every
  adapter must subclass `CloudProvider`, declare capabilities, expose the ABC
  methods, and `available()` must never raise.
- **§109 Incident model / §136 change classification / §137 DoD / §138 phases /
  §139 target architecture / §142 non-goals:** captured below.

## §109 Incident model

Lifecycle: `open → triaged → in_progress → resolved → closed`, plus `reopened`.
Incident record: id, severity (SEV1-4), resource, provider, opened_by, summary,
timeline[], resolved_at, postmortem. DB-backed incident store = BLOCKED (needs DB).

## §136 Change classification

Every release/change tagged `BREAKING | FEATURE | BUGFIX | SECURITY` with a
release-impact note; SECURITY changes get priority + audit entry (already wired
via `audit.add`).

## §137 Definition of Done (DoD)

A PR is Done only when ALL of:
1. code merged + `py_compile` clean;
2. unit test(s) added and passing (`scripts/run_tests.sh`);
3. affected route is under `/api/v1/` with audit where mutating;
4. `TASKS.md` row updated with status + evidence;
5. `docs/`/`STATUS.md` synced (milestone doc-sync, Rule 7).

## §138 Development phases

plan → build → test (this repo) → harden (Iterations 1-9 done) → **production
deploy (BLOCKED: needs owner deploy + external services)** → maintenance.

## §139 / §142 Final architecture & non-goals

Target: Flask API + nginx/systemd, PostgreSQL (ORG→PROJECT→ENV→RESOURCE),
Vault (secrets), Redis/RQ (queue), Prometheus/Grafana (metrics), OPA (policies).
Non-goals (explicit, §142): payment processor, SIEM, general CI/CD, ERP — the
billing module is **tracking/advisory only**.

## BLOCKED — needs owner decision (budget + access)

| Item | § | Requires |
|---|---|---|
| PostgreSQL migration (domain model, audit table, multi-tenancy, RBAC users) | §80, §127 | Postgres deployment; user budget |
| Vault / KMS secrets backend + rotation + MFA store | §29, §68-69 | external service; user budget |
| Redis/RQ or Celery queue + ephemeral workers | §38-41, §74 | Redis; user budget |
| Prometheus + Grafana dashboards, structured logging pipeline | §45, §81-82 | external services; user budget |
| GDPR right-to-delete workflows | §123 | DB + key mgmt |
| OPA/Conftest engine | §67-68 | external binary |
| Live production deploy + TLS + monitoring validation | §4 | droplet access + redeploy |

**Until the owner approves these, Iteration 10 cannot be marked complete**
(hardening is explicitly gated on the user decision per `START_HERE.md`).
