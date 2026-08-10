"""Governance checklist (§76-77, §80) — implemented/pending security matrix.

A small, hand-maintained register of security & governance controls and their
current status. Served read-only at ``GET /api/v1/security/checklist`` so
governance state is queryable by scripts, auditors and AI agents.

Statuses:
    implemented  — verified code path in this repo
    partial      — core exists, follow-up items noted
    blocked      — requires an external service/DB/binary (exact requirement
                   given in ``note``; see ``docs/security-governance-iter8.md``)
    pending      — planned, not started
"""
from __future__ import annotations

SECURITY_CHECKLIST: list[dict] = [
    {
        "id": "sec-001",
        "control": "Encryption at rest",
        "section": "§31",
        "status": "implemented",
        "note": "AES-256-GCM via cryptography primitives; PBKDF2 key from "
        "SKYDASH_SECRETS_KEY (skydash/crypto.py). Vault/KMS backend BLOCKED "
        "(external service).",
    },
    {
        "id": "sec-002",
        "control": "RBAC roles",
        "section": "§33",
        "status": "implemented",
        "note": "admin/operator/readonly + require_role/require_permission "
        "with 403 FORBIDDEN envelope; role from config_store profile "
        "(skydash/rbac.py).",
    },
    {
        "id": "sec-003",
        "control": "Resource-level authorization",
        "section": "§34",
        "status": "partial",
        "note": "Role/permission gates exist; org/project scoping BLOCKED on "
        "domain-model DB (Iter 9/10).",
    },
    {
        "id": "sec-004",
        "control": "Multi-tenancy / tenant isolation",
        "section": "§35-36",
        "status": "blocked",
        "note": "Requires PostgreSQL domain model (Iteration 10).",
    },
    {
        "id": "sec-005",
        "control": "Audit trail",
        "section": "§37",
        "status": "implemented",
        "note": "Append-only JSONL + SHA-256 hash chain, @audited on mutating "
        "admin + API v1 actions (skydash/audit.py). DB-backed audit table "
        "BLOCKED (Iter 10).",
    },
    {
        "id": "sec-006",
        "control": "Rate limiting",
        "section": "§76",
        "status": "implemented",
        "note": "Flask-Limiter on login (5/min) + admin mutations + API "
        "actions.",
    },
    {
        "id": "sec-007",
        "control": "CSRF protection",
        "section": "§77",
        "status": "implemented",
        "note": "Flask-WTF CSRFProtect + /api/csrf-token + AJAX header "
        "interceptor.",
    },
    {
        "id": "sec-008",
        "control": "Input validation",
        "section": "§77-78",
        "status": "partial",
        "note": "Jinja autoescaping active; JSON schema validation pending; "
        "SSRF allowlist pending.",
    },
    {
        "id": "sec-009",
        "control": "Secrets management",
        "section": "§29-30",
        "status": "partial",
        "note": "crypto.py ready + git-ignored env files; Vault / per-env "
        "isolation BLOCKED (external service).",
    },
    {
        "id": "sec-010",
        "control": "Credential rotation",
        "section": "§69",
        "status": "blocked",
        "note": "Requires credential store/DB (Iteration 10).",
    },
    {
        "id": "sec-011",
        "control": "Policy engine",
        "section": "§67-68",
        "status": "partial",
        "note": "In-process policies-as-data evaluate()/allowed() + "
        "prod_shield (skydash/policy.py). OPA/Conftest BLOCKED (external "
        "binary not installed).",
    },
    {
        "id": "sec-012",
        "control": "Environment protection",
        "section": "§107",
        "status": "partial",
        "note": "prod_shield wired into server stop/destroy paths; approval "
        "convention documented; MFA + formal approval system BLOCKED "
        "(§66, §68).",
    },
    {
        "id": "sec-013",
        "control": "Database security",
        "section": "§80",
        "status": "blocked",
        "note": "No PostgreSQL; JSON config file today. Least-privilege DB "
        "user + TLS + pooling ship with the Iter 10 DB migration.",
    },
    {
        "id": "sec-014",
        "control": "File security",
        "section": "§79",
        "status": "pending",
        "note": "No upload surface yet; add size/type limits + non-executable "
        "storage with any future upload feature.",
    },
    {
        "id": "sec-015",
        "control": "MFA",
        "section": "§68",
        "status": "blocked",
        "note": "TOTP at login, required for prod/destructive ops; needs user "
        "store (Iteration 10).",
    },
]


def get_checklist() -> list[dict]:
    """Return a defensive copy of the matrix (callers may not mutate it)."""
    return [dict(entry) for entry in SECURITY_CHECKLIST]


def summary() -> dict:
    """Counts per status, e.g. {"implemented": 5, "partial": 3, ...}."""
    counts: dict[str, int] = {}
    for entry in SECURITY_CHECKLIST:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    return counts