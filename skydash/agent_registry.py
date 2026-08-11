"""Agent enrollment (§96-98): short-lived, single-use, scoped tokens.

A token maps to a scope (project + permissions + expiry). verify() consumes a
token exactly once (single-use) so leaked MyTokens cannot be reused. The
agent→platform transport and live agents are BLOCKED; this module provides the
enrollment/session contract they will use.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentSession:
    token: str
    agent_id: str
    project: str = "*"
    permissions: tuple[str, ...] = ("read",)
    expires_at: float = 0.0
    used: bool = False


_tokens: dict[str, AgentSession] = {}


def issue(agent_id: str, project: str = "*", permissions: tuple[str, ...] = ("read",),
          ttl_seconds: int = 900) -> AgentSession:
    """Issue a single-use enrollment token (default 15-min TTL)."""
    sess = AgentSession(token=secrets.token_urlsafe(24), agent_id=agent_id,
                        project=project, permissions=tuple(permissions),
                        expires_at=time.time() + ttl_seconds)
    _tokens[sess.token] = sess
    return sess


def verify(token: str) -> dict[str, Any]:
    """Validate + consume a token exactly once. Returns session info or an error."""
    sess = _tokens.pop(token, None)
    if sess is None:
        return {"ok": False, "error": "unknown or already-used token", "code": "TOKEN_INVALID"}
    if time.time() > sess.expires_at:
        return {"ok": False, "error": "token expired", "code": "TOKEN_EXPIRED"}
    return {"ok": True, "agent_id": sess.agent_id, "project": sess.project,
            "permissions": list(sess.permissions), "code": "OK"}


def revoke_all() -> None:
    _tokens.clear()
