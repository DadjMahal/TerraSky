"""Tests for db — PostgreSQL persistence layer (psycopg2 mocked).

psycopg2 is not a hard dependency in all environments, so a minimal fake is
injected into sys.modules before importing the module under test.
"""
from __future__ import annotations

import os
import sys
import types
from unittest import mock

import pytest

# --------------------------------------------------------------------------- #
# Fake psycopg2 (installed unconditionally so `import db` always works)       #
# --------------------------------------------------------------------------- #
def _make_fake_psycopg2():
    """Build a module that behaves like psycopg2 for the calls db.py makes."""
    class FakeCursor:
        def __init__(self):
            self.executed = []
            self.last_result = "PostgreSQL 15.0"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, sql):
            self.executed.append(sql)

        def fetchone(self):
            return (self.last_result,)

    class FakeConnection:
        def __init__(self, dsn):
            self.dsn = dsn
            self.closed = False
            self.commits = 0
            self.last_cursor = None

        def cursor(self):
            self.last_cursor = FakeCursor()
            return self.last_cursor

        def commit(self):
            self.commits += 1

        def close(self):
            self.closed = True

    mod = types.ModuleType("psycopg2")
    mod.connections = []
    mod.FakeConnection = FakeConnection

    def connect(dsn):
        conn = FakeConnection(dsn)
        mod.connections.append(conn)
        return conn

    mod.connect = connect
    return mod


FAKE_PSYCOPG2 = _make_fake_psycopg2()
sys.modules.setdefault("psycopg2", FAKE_PSYCOPG2)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db  # noqa: E402


# --------------------------------------------------------------------------- #
# get_database_url                                                             #
# --------------------------------------------------------------------------- #
def test_get_database_url_env_override(monkeypatch):
    monkeypatch.setenv("SKYDASH_DATABASE_URL", "postgresql://u@h/db")
    assert db.get_database_url() == "postgresql://u@h/db"


def test_get_database_url_default(monkeypatch):
    monkeypatch.delenv("SKYDASH_DATABASE_URL", raising=False)
    assert db.get_database_url() == db.DEFAULT_DATABASE_URL


# --------------------------------------------------------------------------- #
# get_connection                                                               #
# --------------------------------------------------------------------------- #
def test_get_connection_uses_resolved_url(monkeypatch):
    monkeypatch.setenv("SKYDASH_DATABASE_URL", "postgresql://x@y:5432/z")
    conn = db.get_connection()
    assert isinstance(conn, FAKE_PSYCOPG2.FakeConnection)
    assert conn.dsn == "postgresql://x@y:5432/z"


# --------------------------------------------------------------------------- #
# ensure_schema                                                                #
# --------------------------------------------------------------------------- #
def test_ensure_schema_opens_own_connection_and_commits(monkeypatch):
    monkeypatch.setenv("SKYDASH_DATABASE_URL", "postgresql://own@h/db")
    db.ensure_schema()
    conn = FAKE_PSYCOPG2.connections[-1]
    assert conn.commits >= 1
    assert conn.closed is True


def test_ensure_schema_executes_schema_sql(monkeypatch):
    monkeypatch.setenv("SKYDASH_DATABASE_URL", "postgresql://own@h/db")
    before = len(FAKE_PSYCOPG2.connections)
    db.ensure_schema()
    conn = FAKE_PSYCOPG2.connections[before]
    # last_cursor.executed holds every statement run through it
    assert any("CREATE TABLE IF NOT EXISTS skydash_meta" in sql
               for sql in conn.last_cursor.executed)


def test_ensure_schema_reuses_passed_connection_and_does_not_close():
    conn = FAKE_PSYCOPG2.FakeConnection("postgresql://p/h/db")
    with mock.patch.object(db, "get_connection", side_effect=AssertionError(
            "must not open its own connection")):
        db.ensure_schema(conn=conn)
    assert conn.closed is False
    assert conn.commits >= 1


# --------------------------------------------------------------------------- #
# healthcheck                                                                  #
# --------------------------------------------------------------------------- #
def test_healthcheck_returns_version(monkeypatch):
    monkeypatch.setenv("SKYDASH_DATABASE_URL", "postgresql://own@h/db")
    version = db.healthcheck()
    assert version is not None


def test_healthcheck_reuses_passed_connection_and_does_not_close():
    conn = FAKE_PSYCOPG2.FakeConnection("postgresql://p/h/db")
    with mock.patch.object(db, "get_connection", side_effect=AssertionError(
            "must not open its own connection")):
        version = db.healthcheck(conn=conn)
    assert conn.closed is False
    assert version is not None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
