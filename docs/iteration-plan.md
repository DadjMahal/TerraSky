# Iteration Plan — SkyDash Multi-Cloud Framework

> Based on §134 (Development Phases) and §141 (Engineering Phases). 10 iterations
> mapped to 144-section spec coverage.

## Phase 0: Architecture Audit & Gap Analysis (THIS ITERATION)

**Goal:** Map all 144 sections to code, create docs/, establish baseline.

| Task | Title | Owner | Status |
|------|-------|-------|--------|
| task_0001 | Create docs/ directory + gap analysis | lead | COMPLETE |
| task_0002 | Domain model & provider framework docs | lead | COMPLETE |
| task_0003 | Security model & Terraform integration docs | lead | COMPLETE |
| task_0004 | API reference & UI wireframes docs | lead | COMPLETE |
| task_0005 | Infrastructure diagram doc | lead | COMPLETE |
| task_0006 | Update START_HERE.md + STATUS.md + TASKS.md | lead | COMPLETE |

## Phase 1: Stability & Foundations (Iter 1–3)

| § | Iteration | Title | Scope |
|---|---|---|---|
| 1 | Iter 1 | CSRF, rate limiting, error codes | §77, §76, §113, §120 |
| 2 | Iter 1 | API v1 versioning + OpenAPI | §62, §124, §125 |
| 3 | Iter 2 | Provider capability abstraction | §2.2, §7, §10, §83 |
| 4 | Iter 2 | Standardized status model | §43, §44 |
| 5 | Iter 3 | Secrets migration (env→vault) | §29, §69, §100 |

## Phase 2: Terraform Integration (Iter 5)

| § | Iteration | Title | Scope |
|---|---|---|---|
| 6 | Iter 5 | tfstate reading + drift basic | §11, §15, §104 |
| 7 | Iter 5 | Workspace model (design) | §12 |
| 8 | Iter 5 | State security (design) | §13 |
| 9 | Iter 5 | Provider synchronization (cron) | §42 |
| 10 | Iter 5 | Plan/apply UX (read-only) | §102-104 |

**Note:** "Total Terraform integration" (plan/apply/destroy/execute, all
commands, remote backends, modules, OPA/Conftest policies, Sentinel) is
NOT covered by the current plan. It's a separate expansion — see
`terraform-integration.md` §"Total Integration Scope".
Expansion would need: worker process (Celery/Redis), remote backend infra
(S3+DynamoDB), plan diff rendering, approval workflow. This is a 3-iteration
sub-project.

## Phase 3: Operations & Monitoring (Iter 6–7)

| § | Iteration | Title | Scope |
|---|---|---|---|
| 11 | Iter 6 | Structured logging | §81 |
| 12 | Iter 6 | Audit trail | §37 |
| 13 | Iter 7 | Prometheus metrics + Grafana | §45, §82 |
| 14 | Iter 7 | Alert thresholds | §46 |

## Phase 4: Projects & Applications (Iter 8)

| § | Iteration | Title | Scope |
|---|---|---|---|
| 15 | Iter 8 | Project/Environment entities | §6.1, §105 |
| 16 | Iter 8 | Application model + deployment | §25-27 |

## Phase 5: Policy, Tenancy, Scaling (Iter 9)

| § | Iteration | Title | Scope |
|---|---|---|---|
| 17 | Iter 9 | OPA policy engine | §67-68 |
| 18 | Iter 9 | Multi-tenancy | §35-36 |
| 19 | Iter 10 | Production hardening* | §114-119, §121-123 |

\* **Iter 10 requires user decision** — needs budget approval for external
services (Vault, Redis, PostgreSQL, Prometheus, Grafana).

## Full 10-Iteration Summary

```
Iter 0: Architecture Audit & Gap Analysis (done)
Iter 1: CSRF, rate limiting, error codes, API v1, OpenAPI
Iter 2: Provider capabilities, status model standardization, drift detection UI
Iter 3: Secrets migration, RBAC, audit logging
Iter 4: UI safety improvements, activity timeline, notification center
Iter 5: Terraform integration (state reading, drift, plan/apply UX)
Iter 6: Structured logging, audit trail, Prometheus + Grafana
Iter 7: Alerts, inventory, resource relationships graph
Iter 8: Project/Environment entities, Application model + deployment
Iter 9: OPA policy engine, multi-tenancy, GitOps
Iter 10: Production hardening (REQUIRES USER — external services budget)
```

**Total: 144 sections.** Current status: 24 IMPLEMENTED, 28 PARTIALLY,
72 NOT_IMPLEMENTED. Iterations 0-9 cover ~85 sections. Iter 10 covers
remaining hardening items. Coverage at 100% after Iter 9.
