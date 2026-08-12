"""PostgreSQL persistence layer for SkyDash (Iteration 10 hardening).

Connects via :mod:`psycopg2` to the ``skydash`` database, idempotently creates
the base schema (``CREATE TABLE IF NOT EXISTS`` — never drops or alters
existing tables), and exposes a :func:`healthcheck` returning the live server
version string.

The connection string is read from ``SKYDASH_DATABASE_URL`` (populated in the
systemd ``EnvironmentFile`` at ``/home/volodro/terraform/.env``) with a local
``127.0.0.1`` fallback for dev.

NOTE: this module is *prepared* for the next app deployment; the running Flask
``skydash.service`` is intentionally NOT restarted by this code.
"""
from __future__ import annotations

import os

import psycopg2

DEFAULT_DATABASE_URL = "postgresql://skydash@127.0.0.1:5432/skydash"

# Idempotent base schema. Only CREATE IF NOT EXISTS — no DROP, no ALTER, so
# pre-existing rows/data are never disturbed.
SCHEMA = """
CREATE TABLE IF NOT EXISTS skydash_meta (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def get_database_url() -> str:
    """Resolve the Postgres connection string from env, else local fallback."""
    return os.environ.get("SKYDASH_DATABASE_URL", DEFAULT_DATABASE_URL)


def get_connection():
    """Open a psycopg2 connection to the SkyDash database (not autocommit)."""
    return psycopg2.connect(get_database_url())


def ensure_schema(conn=None) -> None:
    """Idempotently create the base SkyDash tables (safe to call repeatedly)."""
    own = conn is None
    if own:
        conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    finally:
        if own:
            conn.close()


def healthcheck(conn=None) -> str:
    """Return the live PostgreSQL version string (proves a working connection)."""
    own = conn is None
    if own:
        conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            return cur.fetchone()[0]
    finally:
        if own:
            conn.close()


if __name__ == "__main__":  # pragma: no cover - manual CLI smoke test
    ensure_schema()
    print("healthcheck:", healthcheck())
