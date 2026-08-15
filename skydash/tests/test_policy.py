"""Tests for policy — evaluate(), allowed(), prod_shield().

Pure stdlib. Verifies policy matching, priority ordering, deny-over-allow
tie-break, implicit allow fallback, and the production-environment guard
(§107).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy import (
    evaluate,
    allowed,
    policy_matches,
    prod_shield,
    is_prod_resource,
    DESTRUCTIVE_ACTIONS,
    PROD_TAG_KEYS,
    PROD_TAG_VALUES,
    IMPLICIT_ALLOW_ID,
    DEFAULT_POLICIES,
)

# --------------------------------------------------------------------------- #
# is_prod_resource                                                            #
# --------------------------------------------------------------------------- #
def test_is_prod_resource_env_prod_tag():
    res = {"tags": {"env": "prod"}}
    assert is_prod_resource(res) is True


def test_is_prod_resource_environment_production_tag():
    res = {"tags": {"environment": "production"}}
    assert is_prod_resource(res) is True


def test_is_prod_resource_tier_prod_tag():
    res = {"tags": {"tier": "prod"}}
    assert is_prod_resource(res) is True


def test_is_prod_resource_top_level_environment():
    res = {"environment": "prod"}
    assert is_prod_resource(res) is True


def test_is_prod_resource_top_level_tier():
    res = {"tier": "prod"}
    assert is_prod_resource(res) is True


def test_is_prod_resource_not_prod():
    res = {"tags": {"env": "dev"}}
    assert is_prod_resource(res) is False


def test_is_prod_resource_no_tags():
    assert is_prod_resource({}) is False


def test_is_prod_resource_empty_tags():
    assert is_prod_resource({"tags": {}}) is False


def test_is_prod_resource_case_insensitive():
    res = {"tags": {"env": "PROD"}}
    assert is_prod_resource(res) is True


# --------------------------------------------------------------------------- #
# evaluate / allowed — basic matching                                        #
# --------------------------------------------------------------------------- #
def test_evaluate_server_read_allowed():
    """default-allow-read policy matches server.read."""
    res = {"slug": "web-1"}
    verdicts = evaluate("server.read", res)
    assert len(verdicts) == 1
    assert verdicts[0]["policy_id"] == "default-allow-read"
    assert verdicts[0]["effect"] == "allow"


def test_allowed_server_read():
    assert allowed("server.read", {"slug": "web-1"}) is True


def test_evaluate_no_policy_matched_returns_implicit_allow():
    """When nothing matches, a single implicit-allow verdict is returned."""
    res = {"slug": "web-1"}
    verdicts = evaluate("unknown.action", res)
    assert len(verdicts) == 1
    assert verdicts[0]["policy_id"] == IMPLICIT_ALLOW_ID
    assert verdicts[0]["effect"] == "allow"
    assert verdicts[0]["matched"] is False


def test_evaluate_deny_destroy_prod():
    """deny-destroy-prod (priority 100) overrides default-allow-read."""
    res = {"tags": {"env": "prod"}, "slug": "prod-db"}
    verdicts = evaluate("server.destroy", res)
    assert verdicts[0]["effect"] == "deny"
    assert verdicts[0]["policy_id"] == "deny-destroy-prod"


def test_allowed_deny_destroy_prod():
    assert allowed("server.destroy", {"tags": {"env": "prod"}, "slug": "prod-db"}) is False


def test_evaluate_deny_stop_prod():
    res = {"tags": {"env": "prod"}, "slug": "prod-web"}
    verdicts = evaluate("server.stop", res)
    assert verdicts[0]["effect"] == "deny"
    assert verdicts[0]["policy_id"] == "deny-stop-prod"


def test_evaluate_destroy_non_prod_not_denied():
    """When env is not prod, implicit allow wins for server.destroy."""
    res = {"tags": {"env": "dev"}, "slug": "dev-db"}
    verdicts = evaluate("server.destroy", res)
    assert verdicts[0]["policy_id"] == IMPLICIT_ALLOW_ID
    assert verdicts[0]["effect"] == "allow"


def test_evaluate_priority_ordering():
    """Higher priority always comes first in the verdict list."""
    policies = [
        {"id": "low", "action": "server.*", "effect": "allow", "priority": 1, "reason": "low"},
        {"id": "high", "action": "server.*", "effect": "deny", "priority": 50, "reason": "high"},
    ]
    verdicts = evaluate("server.destroy", {}, policies)
    assert verdicts[0]["policy_id"] == "high"
    assert verdicts[0]["effect"] == "deny"


def test_evaluate_priority_equal_allow_wins():
    """At equal priority, allow wins (matches current sort key semantics)."""
    policies = [
        {"id": "allow", "action": "server.*", "effect": "allow", "priority": 10, "reason": "a"},
        {"id": "deny", "action": "server.*", "effect": "deny", "priority": 10, "reason": "d"},
    ]
    verdicts = evaluate("server.destroy", {}, policies)
    assert verdicts[0]["effect"] == "allow"


def test_evaluate_fnmatch_action_pattern():
    policies = [
        {"id": "wildcard", "action": "server.*", "effect": "allow", "priority": 1, "reason": "x"},
    ]
    verdicts = evaluate("server.read", {}, policies)
    assert len(verdicts) == 1
    assert verdicts[0]["policy_id"] == "wildcard"


def test_evaluate_multiple_matches_all_returned():
    policies = [
        {"id": "p1", "action": "server.*", "effect": "allow", "priority": 5, "reason": "1"},
        {"id": "p2", "action": "server.destroy", "effect": "deny", "priority": 10, "reason": "2"},
    ]
    verdicts = evaluate("server.destroy", {}, policies)
    assert len(verdicts) == 2
    assert verdicts[0]["policy_id"] == "p2"
    assert verdicts[1]["policy_id"] == "p1"


# --------------------------------------------------------------------------- #
# policy_matches — tag / resource / provider conditions                       #
# --------------------------------------------------------------------------- #
def test_policy_matches_tag_condition():
    res = {"tags": {"env": "prod"}}
    pol = {"action": "server.*", "effect": "allow", "when": {"tags": {"env": "prod"}}}
    assert policy_matches(pol, "server.destroy", res) is True


def test_policy_matches_tag_condition_not_met():
    res = {"tags": {"env": "dev"}}
    pol = {"action": "server.*", "effect": "allow", "when": {"tags": {"env": "prod"}}}
    assert policy_matches(pol, "server.destroy", res) is False


def test_policy_matches_resource_pattern():
    res = {"slug": "prod-db-01"}
    pol = {"action": "server.*", "when": {"resource": "prod-*"}}
    assert policy_matches(pol, "server.destroy", res) is True


def test_policy_matches_resource_pattern_not_met():
    res = {"slug": "dev-db-01"}
    pol = {"action": "server.*", "when": {"resource": "prod-*"}}
    assert policy_matches(pol, "server.destroy", res) is False


def test_policy_matches_provider_condition():
    res = {"provider": "aws", "slug": "x"}
    pol = {"action": "server.*", "when": {"provider": "aws"}}
    assert policy_matches(pol, "server.read", res) is True


def test_policy_matches_provider_condition_not_met():
    res = {"provider": "azure", "slug": "x"}
    pol = {"action": "server.*", "when": {"provider": "aws"}}
    assert policy_matches(pol, "server.read", res) is False


def test_policy_matches_no_action_pattern():
    pol = {"effect": "allow", "priority": 1}
    assert policy_matches(pol, "anything", {}) is True


def test_policy_matches_action_exact():
    pol = {"action": "server.read", "effect": "allow", "priority": 1}
    assert policy_matches(pol, "server.read", {}) is True
    assert policy_matches(pol, "server.stop", {}) is False


# --------------------------------------------------------------------------- #
# prod_shield                                                                  #
# --------------------------------------------------------------------------- #
def test_prod_shield_non_destructive_allowed():
    res = {"tags": {"env": "prod"}, "slug": "web-1"}
    result = prod_shield(res, "server.read")
    assert result["allowed"] is True
    assert result["code"] == "OK"
    assert result["prod"] is True
    assert result["destructive"] is False


def test_prod_shield_destructive_non_prod_allowed():
    res = {"tags": {"env": "dev"}, "slug": "web-1"}
    result = prod_shield(res, "server.destroy")
    assert result["allowed"] is True
    assert result["code"] == "OK"
    assert result["prod"] is False
    assert result["destructive"] is True


def test_prod_shield_destructive_prod_denied_without_approval():
    res = {"tags": {"env": "prod"}, "slug": "prod-web"}
    result = prod_shield(res, "server.destroy", approved=False)
    assert result["allowed"] is False
    assert result["code"] == "PROD_SHIELD"
    assert result["prod"] is True
    assert result["destructive"] is True
    assert result["approved"] is False


def test_prod_shield_destructive_prod_allowed_with_approval():
    res = {"tags": {"env": "prod"}, "slug": "prod-web"}
    result = prod_shield(res, "server.destroy", approved=True, approval_ref="TICKET-42")
    assert result["allowed"] is True
    assert result["code"] == "APPROVED"
    assert result["approved"] is True
    assert "TICKET-42" in result["reason"]


def test_prod_shield_destructive_prod_denied_with_approval_false():
    res = {"tags": {"env": "prod"}, "slug": "prod-web"}
    result = prod_shield(res, "server.terminate", approved=False, approval_ref=None)
    assert result["allowed"] is False
    assert result["code"] == "PROD_SHIELD"


def test_prod_shield_resource_name_from_id():
    res = {"tags": {"env": "prod"}, "id": "i-prod-1"}
    result = prod_shield(res, "server.stop", approved=False)
    assert "i-prod-1" in result["reason"]


def test_prod_shield_unknown_resource_name():
    res = {"tags": {"env": "prod"}}
    result = prod_shield(res, "server.stop", approved=False)
    assert "?" in result["reason"]


def test_prod_shield_all_destructive_actions():
    """Every action in DESTRUCTIVE_ACTIONS is recognized as destructive."""
    res = {"tags": {"env": "prod"}}
    for action in DESTRUCTIVE_ACTIONS:
        result = prod_shield(res, action, approved=False)
        assert result["destructive"] is True
        assert result["prod"] is True
        assert result["allowed"] is False


def test_prod_shield_non_listed_action_not_destructive():
    res = {"tags": {"env": "prod"}}
    result = prod_shield(res, "server.read", approved=False)
    assert result["destructive"] is False
    assert result["allowed"] is True


# --------------------------------------------------------------------------- #
# Default policies constant                                                   #
# --------------------------------------------------------------------------- #
def test_default_policies_structure():
    assert len(DEFAULT_POLICIES) == 3
    ids = [p["id"] for p in DEFAULT_POLICIES]
    assert "default-allow-read" in ids
    assert "deny-destroy-prod" in ids
    assert "deny-stop-prod" in ids


def test_prod_tag_keys_and_values():
    assert "env" in PROD_TAG_KEYS
    assert "environment" in PROD_TAG_KEYS
    assert "tier" in PROD_TAG_KEYS
    assert "prod" in PROD_TAG_VALUES
    assert "production" in PROD_TAG_VALUES


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"FAIL  {name}: {exc}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
