"""Tests for agent_registry — agent enrollment with single-use scoped tokens (§96-98).

issue()/verify()/revoke_all() are exercised against an isolated _tokens store.
Time is mocked (or past expiry assigned directly) so token expiry assertions are
deterministic and no real clock or external calls are involved.
"""
from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_registry


@pytest.fixture(autouse=True)
def _isolated_tokens():
    """Start every test with a clean token store."""
    agent_registry.revoke_all()
    yield
    agent_registry.revoke_all()


# --------------------------------------------------------------------------- #
# AgentSession dataclass                                                       #
# --------------------------------------------------------------------------- #
def test_agent_session_defaults():
    sess = agent_registry.AgentSession(token="t", agent_id="a")
    assert sess.project == "*"
    assert sess.permissions == ("read",)
    assert sess.expires_at == 0.0
    assert sess.used is False


def test_agent_session_custom_fields():
    sess = agent_registry.AgentSession(
        token="t", agent_id="a", project="payments",
        permissions=("read", "write"), expires_at=1234.5, used=True)
    assert sess.project == "payments"
    assert sess.permissions == ("read", "write")
    assert sess.expires_at == 1234.5
    assert sess.used is True


def test_agent_session_is_dataclass():
    assert agent_registry.AgentSession.__dataclass_fields__ is not None
# --------------------------------------------------------------------------- #
# issue                                                                         #
# --------------------------------------------------------------------------- #
def test_issue_stores_session_in_token_store():
    sess = agent_registry.issue("agent-1")
    assert sess.token in agent_registry._tokens
    assert agent_registry._tokens[sess.token] is sess


def test_issue_returns_agent_session_with_defaults():
    sess = agent_registry.issue("agent-1")
    assert isinstance(sess, agent_registry.AgentSession)
    assert sess.agent_id == "agent-1"
    assert sess.project == "*"
    assert sess.permissions == ("read",)
    assert sess.used is False


def test_issue_generates_urandom_token():
    with mock.patch.object(agent_registry.secrets, "token_urlsafe",
                           return_value="abc123") as tok:
        sess = agent_registry.issue("agent-1")
    tok.assert_called_once_with(24)
    assert sess.token == "abc123"


def test_issue_applies_scope_and_permissions():
    sess = agent_registry.issue("agent-2", project="l2j", permissions=("read", "write"))
    assert sess.project == "l2j"
    assert sess.permissions == ("read", "write")


def test_issue_normalizes_permissions_list_to_tuple():
    sess = agent_registry.issue("agent-3", permissions=["read", "audit"])
    assert isinstance(sess.permissions, tuple)
    assert sess.permissions == ("read", "audit")


def test_issue_sets_expiry_from_ttl():
    with mock.patch("agent_registry.time.time", return_value=1000.0):
        sess = agent_registry.issue("agent-4", ttl_seconds=300)
    assert sess.expires_at == 1300.0


def test_issue_default_ttl_is_900():
    with mock.patch("agent_registry.time.time", return_value=1000.0):
        sess = agent_registry.issue("agent-5")
    assert sess.expires_at == 1900.0
# --------------------------------------------------------------------------- #
# verify                                                                         #
# --------------------------------------------------------------------------- #
def test_verify_valid_token_returns_session_info():
    sess = agent_registry.issue("agent-1", project="l2j", permissions=("read", "write"))
    result = agent_registry.verify(sess.token)
    assert result["ok"] is True
    assert result["agent_id"] == "agent-1"
    assert result["project"] == "l2j"
    assert result["permissions"] == ["read", "write"]
    assert result["code"] == "OK"


def test_verify_consumes_token_exactly_once():
    sess = agent_registry.issue("agent-1")
    assert agent_registry.verify(sess.token)["ok"] is True
    # second use of the same token must fail — single-use semantics
    second = agent_registry.verify(sess.token)
    assert second["ok"] is False
    assert second["code"] == "TOKEN_INVALID"
    assert "unknown or already-used" in second["error"]


def test_verify_removes_token_from_store():
    sess = agent_registry.issue("agent-1")
    agent_registry.verify(sess.token)
    assert sess.token not in agent_registry._tokens


def test_verify_unknown_token():
    result = agent_registry.verify("bogus-token")
    assert result["ok"] is False
    assert result["code"] == "TOKEN_INVALID"


def test_verify_expired_token():
    sess = agent_registry.issue("agent-1")
    sess.expires_at = 1.0  # long in the past
    result = agent_registry.verify(sess.token)
    assert result["ok"] is False
    assert result["code"] == "TOKEN_EXPIRED"
    assert "expired" in result["error"]


def test_verify_expired_token_is_consumed():
    """Expired tokens are still removed from the store on verification."""
    sess = agent_registry.issue("agent-1")
    sess.expires_at = 1.0
    agent_registry.verify(sess.token)
    assert sess.token not in agent_registry._tokens


def test_verify_not_expired_passes_with_time_mocked():
    sess = agent_registry.issue("agent-1", ttl_seconds=900)
    with mock.patch("agent_registry.time.time", return_value=sess.expires_at - 10):
        result = agent_registry.verify(sess.token)
    assert result["ok"] is True


# --------------------------------------------------------------------------- #
# revoke_all                                                                    #
# --------------------------------------------------------------------------- #
def test_revoke_all_clears_token_store():
    s1 = agent_registry.issue("agent-1")
    s2 = agent_registry.issue("agent-2")
    agent_registry.revoke_all()
    assert agent_registry._tokens == {}
    assert agent_registry.verify(s1.token)["ok"] is False
    assert agent_registry.verify(s2.token)["ok"] is False


def test_verify_permissions_returned_as_list_of_strings():
    sess = agent_registry.issue("agent-7", permissions=("read", "write"))
    result = agent_registry.verify(sess.token)
    assert isinstance(result["permissions"], list)
    assert all(isinstance(p, str) for p in result["permissions"])


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
