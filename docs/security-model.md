# SkyDash Security Model

> **Created:** 2026-08-10 · Source: §29-36, §68, §76-80 + actual `auth.py`, `config_store.py`.
> Current state: single-admin session auth; no RBAC/MFA/audit/secrets/encryption.

## 1. Current (implemented)

- **Auth (§32):** `auth.py` — username/password, Werkzeug `check_password_hash`, 1h session timeout. Admin password from `SKYDASH_ADMIN_PASSWORD` env or stored hash in `skydash_config.json`.
- **Authz (§33):** `login_required` decorator on all Flask routes; admin panel for settings/profile/password.
- **Secrets in git (§124):** `.gitignore` excludes `.env`, `.env.backup`.

## 2. Target Security Stack (gaps to implement)

| Area | Spec | Current | Plan |
|---|---|---|---|
| RBAC | §33 | login_required only | roles: owner/admin/operator/readonly; permission/role/assignment tables |
| Resource-level authz | §34 | none | project+environment scoping; owner/team checks |
| Multi-tenancy | §35-36 | single tenant | org id on all rows; row-level isolation |
| Audit | §37 | none | append-only audit table; every action |
| User/Team | §32 | single admin | users+teams tables, invite/enroll |
| MFA | §68 | none | TOTP at login; required for prod/destructive |
| Secrets | §29-30 | env vars | secrets backend (encrypted), per-env isolation, never returned to UI |
| Encryption | §31 | none | AES-256-GCM at rest for secrets/creds; TLS everywhere |
| Rate limiting | §76 | none | Flask-Limiter / NGINX limit_req |
| Input validation | §77-78 | Template escaping | CSRF tokens, validate redirect next=, SSRF allowlist for endpoints |
| File security | §79 | no uploads | size/type limits, non-executable storage |
| DB security | §80 (future) | JSON file | PostgreSQL least-privilege user, TLS, connection pooling, migrations |

## 3. Credential Handling

- Provider creds live in git-ignored `terraform/.env` (systemd `EnvironmentFile`) — OK.
- Target: encrypted `credentials` table; UI masks secrets (§100); rotation metadata (§69).

## 4. Session & Cookie Flags

- `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE="Lax"`, `SESSION_COOKIE_SECURE` (behind TLS).
- Add CSRF token to all POST forms (Flask-WTF or custom).
# Security Model — SkyDash

> Maps the framework's security requirements (§32–39, §67–68, §75–80, §105–108,
> §122–123) to the current codebase and gaps.

## Current Security State

### Authentication — §32 — IMPLEMENTED
**File:** `skydash/auth.py`

```python
# auth.py:5
login_manager = LoginManager()

# auth.py:24
@login_manager.request_loader / @login_manager.unauthorized_handler
def login_required(f): ...  # wraps routes, checks session['logged_in']

# auth.py
def login_user(password): hash check via werkzeug.security.check_password_hash
def hash_password(pw): generate_password_hash
```

Single `admin` user. Password stored as env var `SKYDASH_ADMIN_PASSWORD`
(plaintext) or in `config_store.py` as a Werkzeug hash (`skydash_config.json`).
No multi-user, no team-based auth, no SSO, no MFA.

### Authorization — §33 — PARTIALLY IMPLEMENTED
**File:** `auth.py:24` — `login_required` decorator on all routes.

No RBAC roles, no resource-level authorization (§34), no multi-tenancy (§35).

### Error Handling — §39, §113 — PARTIALLY IMPLEMENTED
**File:** `app.py`

- `app.py:147-149` — per-instance `try/except` in `_build_instance`: catches
  provider exceptions, sets `instance.error`, continues. Good isolation (§112).
- No normalized error codes (§113) — errors are free-text strings surfaced to UI.
- No retry system (§40) — single attempt, error shown.

### Idempotency — §39 — NOT_IMPLEMENTED
No idempotency keys/tokens. Repeated clicks on start/stop could trigger multiple API calls.
Should implement: idempotency-key header on provider API calls, deduplicate concurrent operations.

### Session — §35 — PARTIALLY IMPLEMENTED
Flask signed cookies (`app.py:41` `app.secret_key`). No Redis-backed sessions.
Session expires when browser closes. No session revocation (§36).

### CSRF Protection — §77 — NOT_IMPLEMENTED
Flask session cookies but no `Flask-WTF`/CSRF token middleware. All POST/PUT/DELETE
routes are login_required but CSRF-vulnerable. **HIGH RISK** — must add CSRF tokens.

### Secrets Management — §29-30 — NOT_IMPLEMENTED
| Secret | Location | Issue |
|---|---|---|
| AWS creds | `terraform/.env` | Plaintext env vars, git-ignored |
| Azure creds | `terraform/.env` | Same |
| OCI creds | `terraform/.env` | Private key path in env |
| Flask secret_key | env var or random `os.urandom(24)` | `app.py:40-41` — regenerated on restart if not set → sessions invalidated |
| Admin password | env var `SKYDASH_ADMIN_PASSWORD` or `config_store.py` hash | — |

No vault, no encryption at rest (§31), no credential rotation (§69),
no secret isolation (§30), no audit trail for secret access (§37).

### Input Sanitization — §77 — NOT_IMPLEMENTED
No `bleach` or input sanitization. Templates use Jinja2 autoescaping (✓),
but API endpoints accept raw JSON without schema validation.

### Rate Limiting — §76 — NOT_IMPLEMENTED
No rate limiting on any endpoint. Brute-force login protection absent.

### File Security — §79 — NOT_IMPLEMENTED
`ssh_bridge.py` handles file transfer; no sanitization of file paths,
no size limits, no quarantine scan.

### Database Security — §80 — NOT_IMPLEMENTED
No database. `config_store.py` persists to `skydash_config.json` (plaintext JSON).
No encryption, no access control on the file, no SQL injection surface.

### Observability & Audit — §81-82, §37 — NOT_IMPLEMENTED
No structured logging, no audit log, no log aggregation. Python `logging`
module used minimally. No tamper-evident log store.

## Risk Register (priority)

| Risk | Impact | Likelihood | Mitigation | § |
|---|---|---|---|---|
| CSRF on all POST routes | Critical | High | Add Flask-WTF CSRF | §77 |
| Credential rotation impossible | High | Medium | Vault + rotation API | §69, §100 |
| No RBAC on instances | High | Medium | Role-based provider gating | §33, §34 |
| No rate limiting | Medium | High | Flask-Limiter | §76 |
| Plaintext secrets in .env | High | Medium | Vault / SOPS encrypted env | §29, §123 |
| No audit log | High | Medium | Structured audit trail | §37, §81 |
| Single admin password | Medium | Medium | MFA, SSO integration | §32 |
| Flask secret_key rotates | Medium | Low | Persist secret_key to env file | app.py:41 |

## Proposed Security Roadmap

### Iteration 1 (short-term)
1. Add CSRF protection (Flask-WTF) to all forms.
2. Persist `app.secret_key` to environment file (don't auto-regenerate).
3. Add `Flask-Limiter` for rate limiting on auth + API endpoints.

### Iteration 3 (medium-term)
4. Migrate secrets to HashiCorp Vault or AWS Secrets Manager.
5. Implement audit logging (structured, append-only).
6. Add basic RBAC: role-based access to destroy/reboot actions.

### Iteration 5 (long-term)
7. Multi-user with SSO (OIDC).
8. Policy engine (OPA/Conftest) for §67-68 governance.
9. Secret isolation per environment (§30).
10. GDPR compliance tooling (§122).
