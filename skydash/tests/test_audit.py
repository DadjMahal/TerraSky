"""Tests for audit — append-only JSONL log with SHA-256 hash chain (§37).

Redirects AUDIT_DIR to a temp directory so no real audit logs are written.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import date
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import audit

# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _isolated_audit_dir(tmp_path, monkeypatch):
    """Redirect audit.AUDIT_DIR and reset the sequence cache."""
    monkeypatch.setattr(audit, "AUDIT_DIR", str(tmp_path))
    monkeypatch.setattr(audit, "_SEQ_CACHE", {})
    yield tmp_path


GENESIS_HASH = hashlib.sha256(b"skydash-audit-genesis").hexdigest()


# --------------------------------------------------------------------------- #
# _canonical / _to_serializable                                               #
# --------------------------------------------------------------------------- #
def test_canonical_is_deterministic():
    rec = {"b": 2, "a": 1}
    assert audit._canonical(rec) == audit._canonical({"a": 1, "b": 2})


def test_canonical_compact_and_sorted():
    rec = {"b": 2, "a": 1}
    result = audit._canonical(rec).decode("utf-8")
    assert result == '{"a":1,"b":2}'


def test_to_serializable_datetime():
    from datetime import datetime
    dt = datetime(2024, 1, 15, 10, 30, 0)
    result = audit._to_serializable(dt)
    assert result == "2024-01-15T10:30:00"


def test_to_serializable_date():
    d = date(2024, 1, 15)
    result = audit._to_serializable(d)
    assert result == "2024-01-15"


def test_to_serializable_set():
    result = audit._to_serializable({"c", "a", "b"})
    assert result == ["a", "b", "c"]


def test_to_serializable_bytes():
    result = audit._to_serializable(b"hello")
    assert result == "hello".encode().hex()


def test_to_serializable_passthrough():
    assert audit._to_serializable(42) == 42
    assert audit._to_serializable("text") == "text"
    assert audit._to_serializable(None) is None


# --------------------------------------------------------------------------- #
# add — record creation                                                         #
# --------------------------------------------------------------------------- #
def test_add_returns_record_with_seq_and_hash():
    rec = audit.add("alice", "server.read", "instances/web-1")
    assert rec["actor"] == "alice"
    assert rec["action"] == "server.read"
    assert rec["resource"] == "instances/web-1"
    assert rec["outcome"] == "success"
    assert rec["seq"] == 1
    assert rec["prev_hash"] == GENESIS_HASH
    assert "hash" in rec
    assert "ts" in rec


def test_add_includes_detail_when_provided():
    rec = audit.add("bob", "settings.update", "config",
                    detail={"key": "timeout", "value": 30}, ip="10.0.0.1")
    assert rec["detail"] == {"key": "timeout", "value": 30}
    assert rec["ip"] == "10.0.0.1"
    assert rec["outcome"] == "success"


def test_add_omits_detail_when_none():
    rec = audit.add("bob", "settings.update", "config")
    assert "detail" not in rec


def test_add_anonymous_actor():
    rec = audit.add(None, "server.read", "instances/x")
    assert rec["actor"] == "anonymous"


def test_add_empty_actor_defaults_to_anonymous():
    rec = audit.add("", "server.read", "instances/x")
    assert rec["actor"] == "anonymous"


def test_add_outcome_error():
    rec = audit.add("alice", "server.destroy", "instances/x", outcome="error")
    assert rec["outcome"] == "error"


def test_add_outcome_denied():
    rec = audit.add("alice", "server.stop", "instances/x", outcome="denied")
    assert rec["outcome"] == "denied"


def test_add_seq_increments():
    r1 = audit.add("alice", "server.read", "x")
    r2 = audit.add("alice", "server.read", "x")
    r3 = audit.add("alice", "server.read", "x")
    assert r1["seq"] == 1
    assert r2["seq"] == 2
    assert r3["seq"] == 3


def test_add_hash_chain_links_records():
    r1 = audit.add("alice", "server.read", "x")
    r2 = audit.add("alice", "server.stop", "x")
    assert r2["prev_hash"] == r1["hash"]


def test_add_writes_to_jsonl_file():
    audit.add("alice", "server.read", "x")
    audit.add("alice", "server.stop", "x")
    day = audit._today()
    filepath = audit._filename(day)
    with open(filepath, "r") as f:
        lines = f.read().strip().split("\n")
    assert len(lines) == 2
    rec1 = json.loads(lines[0])
    rec2 = json.loads(lines[1])
    assert rec1["seq"] == 1
    assert rec2["seq"] == 2
    assert rec2["prev_hash"] == rec1["hash"]


def test_add_creates_audit_dir():
    audit.add("alice", "server.read", "x")
    day = audit._today()
    filepath = audit._filename(day)
    assert os.path.exists(filepath)


# --------------------------------------------------------------------------- #
# _read_tail — chain seeding                                                  #
# --------------------------------------------------------------------------- #
def test_read_tail_empty_file():
    """When no file exists, returns (0, genesis_hash)."""
    day = "2024-01-01"
    seq, h = audit._read_tail(day)
    assert seq == 0
    assert h == GENESIS_HASH


def test_read_tail_existing_file():
    """After writing records, _read_tail returns last seq + hash."""
    audit.add("alice", "server.read", "x")
    audit.add("alice", "server.stop", "x")
    day = audit._today()
    seq, h = audit._read_tail(day)
    assert seq == 2
    assert h != GENESIS_HASH


def test_read_tail_skips_blank_lines():
    """Blank lines in the file are ignored by _read_tail."""
    day = "2024-01-01"
    filepath = audit._filename(day)
    with open(filepath, "w") as f:
        f.write(json.dumps({"seq": 1, "action": "x"}) + "\n")
        f.write("\n")
        f.write(json.dumps({"seq": 2, "action": "y"}) + "\n")
    audit._SEQ_CACHE.clear()
    seq, h = audit._read_tail(day)
    assert seq == 2


# --------------------------------------------------------------------------- #
# _iter_records                                                                 #
# --------------------------------------------------------------------------- #
def test_iter_records_yields_all():
    audit.add("a", "server.read", "x")
    audit.add("b", "server.read", "x")
    day = audit._today()
    records = list(audit._iter_records(audit._filename(day)))
    assert len(records) == 2
    assert records[0]["actor"] == "a"
    assert records[1]["actor"] == "b"


def test_iter_records_skips_corrupt_lines():
    """Corrupt lines are skipped, valid lines after them still parse."""
    day = "2024-01-01"
    filepath = audit._filename(day)
    with open(filepath, "w") as f:
        f.write(json.dumps({"seq": 1, "action": "x"}) + "\n")
        f.write("{ this is broken json\n")
        f.write(json.dumps({"seq": 2, "action": "y"}) + "\n")
    records = list(audit._iter_records(filepath))
    assert len(records) == 2
    assert records[0]["seq"] == 1
    assert records[1]["seq"] == 2


def test_iter_records_missing_file_returns_empty():
    records = list(audit._iter_records(audit._filename("1999-01-01")))
    assert records == []


# --------------------------------------------------------------------------- #
# query                                                                         #
# --------------------------------------------------------------------------- #
def test_query_returns_all_for_day():
    audit.add("alice", "server.read", "x")
    audit.add("bob", "server.stop", "y")
    results = audit.query()
    assert len(results) == 2


def test_query_by_action():
    audit.add("alice", "server.read", "x")
    audit.add("bob", "server.stop", "y")
    results = audit.query(action="server.read")
    assert len(results) == 1
    assert results[0]["actor"] == "alice"


def test_query_by_actor():
    audit.add("alice", "server.read", "x")
    audit.add("bob", "server.stop", "y")
    results = audit.query(actor="bob")
    assert len(results) == 1
    assert results[0]["actor"] == "bob"


def test_query_by_resource():
    audit.add("alice", "server.read", "instances/web-1")
    audit.add("bob", "server.stop", "instances/db-1")
    results = audit.query(resource="instances/web-1")
    assert len(results) == 1
    assert results[0]["resource"] == "instances/web-1"


def test_query_multiple_filters():
    audit.add("alice", "server.read", "instances/web-1")
    audit.add("alice", "server.stop", "instances/web-2")
    audit.add("bob", "server.read", "instances/web-1")
    results = audit.query(actor="alice", resource="instances/web-1")
    assert len(results) == 1
    assert results[0]["action"] == "server.read"


def test_query_limit():
    for i in range(10):
        audit.add("actor", f"action.{i}", "res")
    results = audit.query(limit=3)
    assert len(results) == 3


def test_query_returns_newest_first():
    audit.add("a", "action.one", "x")
    audit.add("b", "action.two", "x")
    results = audit.query()
    assert results[0]["seq"] == 2
    assert results[1]["seq"] == 1


def test_query_all_days():
    """Query across all days with '*'; also test _list_days."""
    audit.add("alice", "server.read", "x")
    days = audit._list_days()
    assert len(days) == 1
    assert days[0] == audit._today()
    results = audit.query(day="*", limit=100)
    assert len(results) == 1


def test_query_empty_dir():
    results = audit.query(day="*")
    assert results == []


# --------------------------------------------------------------------------- #
# verify_chain — hash chain integrity                                         #
# --------------------------------------------------------------------------- #
def test_verify_chain_undisturbed_chain():
    audit.add("alice", "server.read", "x")
    audit.add("bob", "server.stop", "y")
    result = audit.verify_chain()
    assert result["ok"] is True
    assert result["checked"] == 2
    assert result["broken"] == 0
    assert result["first_break"] == ""


def test_verify_chain_single_record():
    audit.add("alice", "server.read", "x")
    result = audit.verify_chain()
    assert result["ok"] is True
    assert result["checked"] == 1


def test_verify_chain_no_records():
    result = audit.verify_chain()
    assert result["ok"] is True
    assert result["checked"] == 0
    assert result["broken"] == 0


def test_verify_chain_detects_tampered_prev_hash():
    """Mutate prev_hash of the 2nd record → chain breaks."""
    audit.add("alice", "server.read", "x")
    audit.add("bob", "server.stop", "y")
    day = audit._today()
    filepath = audit._filename(day)
    with open(filepath, "r") as f:
        lines = f.read().strip().split("\n")
    rec2 = json.loads(lines[1])
    rec2["prev_hash"] = "deadbeef" * 8
    with open(filepath, "w") as f:
        f.write(lines[0] + "\n")
        f.write(json.dumps(rec2) + "\n")
    result = audit.verify_chain()
    assert result["ok"] is False
    assert result["broken"] == 1
    assert result["first_break"] == f"{day}:2"


def test_verify_chain_detects_tampered_field():
    """Changing any field breaks the hash chain."""
    audit.add("alice", "server.read", "x")
    audit.add("bob", "server.stop", "y")
    day = audit._today()
    filepath = audit._filename(day)
    with open(filepath, "r") as f:
        lines = f.read().strip().split("\n")
    rec1 = json.loads(lines[0])
    rec1["actor"] = "hacker"
    with open(filepath, "w") as f:
        f.write(json.dumps(rec1) + "\n")
        f.write(lines[1] + "\n")
    result = audit.verify_chain()
    assert result["ok"] is False
    assert result["broken"] >= 1


def test_verify_chain_all_days():
    audit.add("alice", "server.read", "x")
    result = audit.verify_chain(day="*")
    assert result["ok"] is True
    assert result["checked"] == 1


def test_verify_chain_specific_day():
    audit.add("alice", "server.read", "x")
    result = audit.verify_chain(day=audit._today())
    assert result["ok"] is True
    assert result["checked"] == 1


def test_verify_chain_hash_field_excluded():
    """The 'hash' field itself is excluded from its own hash computation."""
    audit.add("alice", "server.read", "x")
    audit.add("bob", "server.stop", "x")
    audit._SEQ_CACHE.clear()
    result = audit.verify_chain()
    assert result["ok"] is True


# --------------------------------------------------------------------------- #
# audited — decorator                                                           #
# --------------------------------------------------------------------------- #
def test_audited_decorator_wraps_and_appends():
    """The audited decorator records a success entry after the view runs."""
    from flask import Flask
    app = Flask(__name__)
    app.secret_key = "test"

    with app.test_request_context("/api/test", headers={"X-Forwarded-For": "203.0.113.1"}):
        from flask import session
        session["user_id"] = "tester"

        @audit.audited()
        def view():
            return ("ok", 200)

        result = view()
        assert result == ("ok", 200)

    records = audit.query(day="*")
    assert len(records) == 1
    assert records[0]["outcome"] == "success"


def test_audited_decorator_records_error_on_exception():
    """The audited decorator records an error entry on exception, then re-raises."""
    from flask import Flask
    app = Flask(__name__)
    app.secret_key = "test"

    with app.test_request_context("/api/test"):
        from flask import session
        session["user_id"] = "tester"

        @audit.audited()
        def view():
            raise ValueError("something broke")

        try:
            view()
            assert False, "Should have raised"
        except ValueError as e:
            assert "something broke" in str(e)

    records = audit.query(day="*")
    assert len(records) == 1
    assert records[0]["outcome"] == "error"
    assert "something broke" in records[0]["detail"]["error"]


def test_status_of_int_result():
    assert audit._status_of(200) == 200


def test_status_of_tuple_with_int():
    assert audit._status_of(("body", 404)) == 404


def test_status_of_tuple_without_int():
    assert audit._status_of(("body", "text")) == 200


def test_status_of_response_object():
    resp = mock.Mock()
    resp.status_code = 201
    assert audit._status_of(resp) == 201


def test_status_of_response_without_status_code():
    assert audit._status_of({"not": "a response"}) == 200


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
