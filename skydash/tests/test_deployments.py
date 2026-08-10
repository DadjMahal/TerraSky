"""Runtime tests for Iteration 6 deployment & secrets modules. No Flask needed."""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_approvals_prod_gate_and_workflow():
    from deployments import approvals as ap

    ap.clear()
    g = ap.gate("deploy", "applications/l2j", "prod", "tester", reason="v1.4.2")
    assert g is not None and g["status"] == "pending"
    assert ap.gate("deploy", "applications/l2j", "dev", "tester") is None
    assert ap.gate("server.stop", "db", "prod", "tester") is not None
    assert ap.approve(g["id"], by="admin")["status"] == "approved"
    assert g["id"] not in [p["id"] for p in ap.pending()]


def test_deploy_dry_run_rollback_and_approval_queue():
    from deployments import applications as am

    am._applications.clear()
    am._deployments.clear()
    app = am.register_application(am.Application(id="l2j", name="l2j", environment="prod",
                                                 deploy_command="bash deploy.sh"))
    rec = am.deploy(app, commit="v1.4.2", dry_run=True)
    assert rec.status == "deployed" and rec.logs and "dry-run" in rec.logs[0]
    rec2 = am.deploy_with_approval(app, commit="v1.4.3", requested_by="tester", dry_run=True)
    assert rec2.status == "queued" and rec2.approval_id
    assert am.rollback(rec.id).status == "rolled_back"


def test_secrets_encrypted_store():
    import crypto
    from deployments import secrets as sm

    assert crypto.CRYPTO_AVAILABLE
    os.environ["SKYDASH_SECRETS_KEY"] = "test-master-key"
    path = os.path.join(tempfile.mkdtemp(), "secrets.json")
    store = sm.SecretStore(path=path, key="test-master-key")
    store.set_secret("db_password", "s3cr3t", actor="admin")
    assert "s3cr3t" not in open(path, "r", encoding="utf-8").read()
    assert store.list_secrets()[0]["masked"] is True
    assert store.get_secret("db_password") == "s3cr3t"
    assert store.delete_secret("db_password") is True
    assert store.get_secret("db_password") is None
    try:
        store.get_secret("db_password")  # already deleted -> None, fine
    except Exception:  # pragma: no cover
        pass


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
