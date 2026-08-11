"""Runtime tests for Iteration 9 AI-agent integration modules. No Flask needed."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_plugins_registry_least_privilege():
    import plugins as pl

    pl.clear()  # wipe, then re-register the built-in example
    from plugins.example_status import status_plugin
    pl.register(status_plugin)
    assert pl.enforce(status_plugin, "status.read") is True
    assert pl.enforce(status_plugin, "server.stop") is False
    assert any(p["name"] == "status-reader" for p in pl.list_plugins())


def test_worker_allowlist_timeout_approval():
    from workers import run_isolated

    ok = run_isolated("uptime")
    assert ok["ok"] is True and ok["code"] == "OK"
    denied = run_isolated("curl -s http://evil.example")
    assert denied["code"] == "NOT_ALLOWED"
    need_approval = run_isolated("systemctl stop nginx", require_approval=True)
    assert need_approval["code"] == "NEEDS_APPROVAL"


def test_agent_registry_token_single_use():
    from agent_registry import issue, verify, revoke_all

    revoke_all()
    sess = issue("agent-1", project="l2j", permissions=("read",), ttl_seconds=60)
    first = verify(sess.token)
    assert first["ok"] and first["project"] == "l2j"
    assert verify(sess.token)["ok"] is False  # single-use consumed


def test_agent_protocol_validation():
    from agent_protocol import validate, rules_payload

    assert validate({"task_type": "status", "resource_id": "aws-hermes"})["ok"] is True
    d = validate({"task_type": "destroy", "resource_id": "prod-db", "intent": ""})
    assert d["ok"] is False and d["requires_approval"] is True
    d2 = validate({"task_type": "destroy", "resource_id": "prod-db", "intent": "decommission per RFC", "approval": True})
    assert d2["ok"] is True
    assert any(r["id"] == "R1" for r in rules_payload())


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
