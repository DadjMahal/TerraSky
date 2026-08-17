"""Runtime tests for the Iteration 8 security & governance modules.

Pure stdlib / cryptography — these run WITHOUT Flask, so they can be verified
in any environment that has the repo's Python deps (only ``cryptography`` is
needed for the crypto round-trip tests).

Run:    python3 tests/test_governance.py          # plain runner
   or   python3 -m pytest tests/test_governance.py -v   # when pytest exists
"""
from __future__ import annotations

import os
import sys
import tempfile

# Make repo modules importable when run from anywhere (tests live in skydash/tests)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- Audit: append-only hash chain ------------------------------------------
def test_audit_hash_chain_append_query_tamper():
    import audit  # noqa: F401
    # audit may already be imported by other test files, so the env var set at
    # import time is ignored here. Redirect the module's dir + chain cache
    # explicitly (mirrors the autouse fixture in test_audit.py) for isolation.
    audit.AUDIT_DIR = tempfile.mkdtemp(prefix="audit-test-")
    audit._SEQ_CACHE.clear()

    r1 = audit.add("tester", "server.stop", "instances/aws-hermes", detail={"status": 200}, ip="127.0.0.1")
    r2 = audit.add("tester", "server.start", "instances/aws-hermes")
    assert abs(int(r2["seq"]) - int(r1["seq"])) == 1
    assert r2["prev_hash"] == r1["hash"], "record 2 must chain from record 1"
    assert audit.verify_chain()["ok"], "fresh chain must verify"
    assert audit.verify_chain()["checked"] == 2

    q = audit.query(action="server.start")
    assert len(q) == 1 and q[0]["action"] == "server.start"

    # Tamper: a hand-appended (non-chained) record must break verification.
    day = audit._today()
    with open(audit._filename(day), "a", encoding="utf-8") as fh:
        fh.write('{"_evil": true}\n')
    res = audit.verify_chain()
    assert not res["ok"] and res["broken"] >= 1


# --- Policy engine + prod shield --------------------------------------------
def test_policy_prod_shield():
    import policy

    prod = {"slug": "prod-db", "tags": {"env": "prod"}}
    dev = {"slug": "dev-web", "tags": {"env": "dev"}}

    assert policy.prod_shield(prod, "server.stop", approved=False)["code"] == "PROD_SHIELD"
    assert policy.prod_shield(prod, "server.stop", approved=True)["allowed"] is True
    assert policy.prod_shield(dev, "server.destroy", approved=False)["allowed"] is True
    assert policy.prod_shield(prod, "server.read")["allowed"] is True  # non-destructive
    assert policy.allowed("server.stop", prod, policy.DEFAULT_POLICIES) is False
    assert policy.allowed("server.read", prod) is True


# --- RBAC role hierarchy -----------------------------------------------------
def test_rbac_role_hierarchy():
    import rbac

    assert rbac.role_can("admin", "server.destroy") is True          # explicit "*"
    assert rbac.role_can("operator", "server.stop") is True          # explicit
    assert rbac.role_can("operator", "server.read") is True          # inherits from readonly
    assert rbac.role_can("readonly", "server.read") is True
    assert rbac.role_can("readonly", "server.stop") is False         # no escalation
    assert rbac.role_can("operator", "server.destroy") is False      # no escalation
    assert rbac.normalize_role("garbage") == "admin"


# --- Crypto: AES-256-GCM round-trip + tamper rejection -----------------------
def test_crypto_roundtrip_and_tamper():
    import crypto

    assert crypto.CRYPTO_AVAILABLE, "cryptography must be present (transitive via paramiko)"
    os.environ["SKYDASH_SECRETS_KEY"] = "test-master-key"
    secret = "sup3r-secret"
    token = crypto.encrypt(secret, crypto.master_key())
    assert crypto.decrypt(token, crypto.master_key()) == secret
    try:
        crypto.decrypt(token, "wrong-master-key")
    except Exception:  # noqa: BLE001 - AES-GCM authentication must reject wrong key
        wrong_key_rejected = True
    else:
        wrong_key_rejected = False
    assert wrong_key_rejected, "decrypt with wrong key must fail authentication"
    st = crypto.selftest()
    assert st["ok"], st


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