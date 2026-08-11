"""AI-agent task protocol (§134) + safety rules (§133, §135).

Agents interact with the platform through the SAME API the UI uses. A
submission is validated: destructive task types require an explicit ``intent``
(explain reasoning) and an ``approval`` flag — matching §133/§135. The platform
audits every action and rate-limits (§76).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DESTRUCTIVE_TASK_TYPES = frozenset({"destroy", "terminate", "stop", "rollback", "terraform.apply", "resource.delete"})

# Human + machine-readable safety rules surfaced via GET /api/v1/agent-rules.
SAFETY_RULES: list[dict[str, str]] = [
    {"id": "R1", "rule": "no destructive action without explicit approval (§133)"},
    {"id": "R2", "rule": "always explain reasoning in the task intent field (§133)"},
    {"id": "R3", "rule": "every action is audited and rate limited (§37, §76, §135)"},
    {"id": "R4", "rule": "commands are sandboxed with timeout, output cap and allowlist (§75)"},
    {"id": "R5", "rule": "agents never receive secret values — secrets are referenced by ID (§29-30)"},
]


@dataclass
class TaskSubmission:
    task_type: str
    resource_id: str
    params: dict = field(default_factory=dict)
    intent: str = ""
    project_scope: str = "*"
    approval: bool = False


def validate(sub: dict) -> dict[str, Any]:
    """Validate a submission dict -> {"ok","errors","requires_approval"}."""
    tt = (sub.get("task_type") or "").strip()
    rid = (sub.get("resource_id") or "").strip()
    intent = (sub.get("intent") or "").strip()
    errors = []
    if not tt:
        errors.append("task_type required")
    if not rid:
        errors.append("resource_id required")
    destructive = tt in DESTRUCTIVE_TASK_TYPES
    requires_approval = False
    if destructive:
        if not intent:
            errors.append("destructive tasks require an explicit intent (explain reasoning; §133)")
        if not sub.get("approval"):
            requires_approval = True
            errors.append("destructive task not approved — send approval=true (§135)")
    return {"ok": not errors, "errors": errors, "requires_approval": requires_approval}


def rules_payload() -> list[dict]:
    return [dict(r) for r in SAFETY_RULES]
