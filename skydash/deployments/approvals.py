"""Approval workflow (§66) — gate mutating/deploy actions.

DB-less by design: an in-process registry with an optional JSONL append-only
log (git-ignored). The real approval system (per-org workflows, MFA §68,
multi-signer) is an Iteration 10 item on the domain-model DB; this module
provides the working gate the deploy engine uses today and is unit-testable.

Lifecycle: ``create()`` -> ``approve()``/``deny()``; ``gate()`` creates an
approval only when the action is on the REQUIRES_APPROVAL list for the given
environment (prod), so non-prod/read flows stay zero-friction.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

APPROVAL_LOG = os.environ.get("SKYDASH_APPROVAL_LOG", "approval_log.jsonl")

# Actions that must never happen on production without an approval record.
REQUIRES_APPROVAL = frozenset({"deploy", "rollback", "destroy", "terraform.apply", "server.stop"})


@dataclass
class Approval:
    id: str
    action: str
    resource: str
    requested_by: str
    reason: str = ""
    environment: str = "staging"
    status: str = "pending"  # pending|approved|denied
    approved_by: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


_store: dict[str, Approval] = {}


def _append_log(rec: dict) -> None:
    try:
        with open(APPROVAL_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    except OSError:  # pragma: no cover - logging must never break the flow
        pass


def create(action: str, resource: str, requested_by: str, environment: str = "staging", reason: str = "") -> Approval:
    appr = Approval(id=uuid.uuid4().hex[:12], action=action, resource=resource,
                    requested_by=requested_by, reason=reason, environment=environment)
    _store[appr.id] = appr
    _append_log({"event": "created", "approval": asdict(appr)})
    return appr


def get(approval_id: str) -> dict | None:
    a = _store.get(approval_id)
    return asdict(a) if a else None


def pending() -> list[dict]:
    return [asdict(a) for a in _store.values() if a.status == "pending"]


def approve(approval_id: str, by: str) -> dict:
    if approval_id not in _store:
        raise KeyError(f"no approval {approval_id}")
    a = _store[approval_id]
    a.status = "approved"
    a.approved_by = by
    a.updated_at = time.time()
    _append_log({"event": "approved", "approval_id": approval_id, "by": by})
    return asdict(a)


def deny(approval_id: str, by: str) -> dict:
    if approval_id not in _store:
        raise KeyError(f"no approval {approval_id}")
    a = _store[approval_id]
    a.status = "denied"
    a.approved_by = by
    a.updated_at = time.time()
    _append_log({"event": "denied", "approval_id": approval_id, "by": by})
    return asdict(a)


def gate(action: str, resource: str, environment: str, requested_by: str, reason: str = "") -> dict | None:
    """Return an approval dict when this action requires one, else None (§66)."""
    if environment == "prod" and action in REQUIRES_APPROVAL:
        return asdict(create(action, resource, requested_by, environment=environment, reason=reason))
    return None


def clear() -> None:
    """Test helper: wipe the in-process registry."""
    _store.clear()
