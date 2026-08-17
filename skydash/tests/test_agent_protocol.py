"""Tests for agent_protocol — task submission validation + safety rules (§133–§135).

Pure stdlib; no Flask/cloud SDK needed. Verifies destructive task handling,
the requires_approval flow, whitespace-normalisation and the safety rules
surface exposed via GET /api/v1/agent-rules.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_protocol import (
    DESTRUCTIVE_TASK_TYPES,
    SAFETY_RULES,
    TaskSubmission,
    rules_payload,
    validate,
)

# --------------------------------------------------------------------------- #
# Constants / data model                                                      #
# --------------------------------------------------------------------------- #
def test_destructive_task_types_content():
    assert isinstance(DESTRUCTIVE_TASK_TYPES, frozenset)
    for expected in ("destroy", "terminate", "stop", "rollback",
                     "terraform.apply", "resource.delete"):
        assert expected in DESTRUCTIVE_TASK_TYPES


def test_safety_rules_has_five_rules():
    assert len(SAFETY_RULES) == 5


def test_safety_rules_have_ids_and_rule_text():
    ids = [r["id"] for r in SAFETY_RULES]
    assert ids == ["R1", "R2", "R3", "R4", "R5"]
    for rule in SAFETY_RULES:
        assert rule["id"]
        assert rule["rule"]


def test_task_submission_defaults():
    sub = TaskSubmission(task_type="server.read", resource_id="web-1")
    assert sub.task_type == "server.read"
    assert sub.resource_id == "web-1"
    assert sub.params == {}
    assert sub.intent == ""
    assert sub.project_scope == "*"
    assert sub.approval is False


def test_task_submission_explicit_values():
    sub = TaskSubmission(
        task_type="destroy",
        resource_id="db-1",
        params={"force": True},
        intent="decommissioning unused dev db",
        project_scope="legacy/old",
        approval=True,
    )
    assert sub.approval is True
    assert sub.project_scope == "legacy/old"
    assert sub.params == {"force": True}


# --------------------------------------------------------------------------- #
# validate()                                                                  #
# --------------------------------------------------------------------------- #
def test_validate_non_destructive_ok():
    result = validate({"task_type": "server.read", "resource_id": "web-1"})
    assert result["ok"] is True
    assert result["errors"] == []
    assert result["requires_approval"] is False


def test_validate_missing_task_type():
    result = validate({"resource_id": "web-1"})
    assert result["ok"] is False
    assert "task_type required" in result["errors"]


def test_validate_missing_resource_id():
    result = validate({"task_type": "server.read"})
    assert result["ok"] is False
    assert "resource_id required" in result["errors"]


def test_validate_empty_submission():
    result = validate({})
    assert result["ok"] is False
    assert result["requires_approval"] is False
    assert "task_type required" in result["errors"]
    assert "resource_id required" in result["errors"]


def test_validate_destructive_without_intent():
    result = validate({"task_type": "destroy", "resource_id": "db-1"})
    assert result["ok"] is False
    assert any("intent" in e for e in result["errors"])
    assert result["requires_approval"] is True


def test_validate_destructive_without_approval():
    result = validate({
        "task_type": "destroy",
        "resource_id": "db-1",
        "intent": "decommissioning no-longer-needed db",
    })
    assert result["ok"] is False
    assert result["requires_approval"] is True
    assert any("approval" in e for e in result["errors"])


def test_validate_destructive_with_intent_and_approval_ok():
    result = validate({
        "task_type": "terminate",
        "resource_id": "i-123",
        "intent": "removing terminated instance",
        "approval": True,
    })
    assert result["ok"] is True
    assert result["errors"] == []
    assert result["requires_approval"] is False


def test_validate_trimmed_whitespace():
    result = validate({
        "task_type": "  server.read  ",
        "resource_id": "  web-1  ",
        "intent": "  ",
    })
    assert result["ok"] is True
    assert result["requires_approval"] is False


def test_validate_non_destructive_does_not_require_approval():
    result = validate({
        "task_type": "server.read",
        "resource_id": "web-1",
        "approval": False,
    })
    assert result["requires_approval"] is False
    assert result["ok"] is True


def test_validate_unknown_task_type_treated_read_only():
    result = validate({"task_type": "some.custom.task", "resource_id": "x"})
    assert result["ok"] is True
    assert result["requires_approval"] is False


# --------------------------------------------------------------------------- #
# rules_payload()                                                             #
# --------------------------------------------------------------------------- #
def test_rules_payload_matches_safety_rules():
    payload = rules_payload()
    assert payload == SAFETY_RULES


def test_rules_payload_returns_copies():
    payload = rules_payload()
    payload[0]["id"] = "MUTATED"
    assert SAFETY_RULES[0]["id"] == "R1"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))

