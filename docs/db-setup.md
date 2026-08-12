# SkyDash — Database & Queue Setup (Iteration 10 Hardening)

This document describes the persistent/queue layer provisioned on the
DigitalOcean droplet `167.172.188.248` (Ubuntu 24.04) for running SkyDash: a
**PostgreSQL 16** instance for persistence and a **Redis 7** instance for
caching/queues. It is written for the team so the app-deployment teammate can
wire up `skydash/db.py` without re-discovering the details.

## Services

| Service   | Version            | Systemd unit     | Status     | Listens on |
|-----------|--------------------|------------------|------------|-------------|
| PostgreSQL| 16.14              | `postgresql`     | active/enabled | 127.0.0.1:5432 |
| Redis     | 7.0.15             | `redis-server`   | active/enabled | 127.0.0.1:6379 |

Both are bound to localhost only — not exposed publicly.

## Least-privilege DB user + database

Created against the default `postgres` superuser (peer auth):

- Role: **`skydash`** — `LOGIN` only. It is **NOT** superuser,
  `CREATEDB`, `CREATEROLE`, or replication. Lease-privilege by design:
  the app can only read/write the `skydash` database.
- Database: **`skydash`** (owner `skydash`), fresh — no pre-existing tables
  or data were dropped or altered.

Connection string (password **masked** here):

```
postgresql://skydash:*****@127.0.0.1:5432/skydash
```

The real password lives in the systemd `EnvironmentFile`:

```
/home/volodro/terraform/.env
SKYDASH_DATABASE_URL=postgresql://skydash:<real-password>@127.0.0.1:5432/skydash
```

`skydash.service` already loads this file, so a future app restart that reads
`SKYDASH_DATABASE_URL` (as `skydash/db.py` does) will pick the credentials up
automatically. The file is mode `0600`/owned by `volodro`.

## Verification (real output)

```sql
postgresql://skydash:*****@127.0.0.1:5432/skydash> select version();
PostgreSQL 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1) on x86_64-pc-linux-gnu,
compiled by gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0, 64-bit
```

```bash
$ redis-cli ping
PONG

$ systemctl is-active postgresql redis-server   # both -> active
$ systemctl is-enabled postgresql redis-server  # both -> enabled
```

```sql
-- least-privilege check (all f, f, f, f = not superuser/createdb/createrole/rep)
rollname | rolsuper | rolcreatedb | rolcreaterole | rolreplication | rolcanlogin
skydash  | f        | f           | f             | f              | t
```

## `skydash/db.py`

`/root/TerraSky/skydash/db.py` is the persistent-layer module for the app:

- `get_connection()` — opens a `psycopg2` connection using
  `SKYDASH_DATABASE_URL` (fallback `postgresql://skydash@127.0.0.1:5432/skydash`).
- `ensure_schema()` — idempotent `CREATE TABLE IF NOT EXISTS skydash_meta …`
  (never drops/alters existing data).
- `healthcheck()` — returns `SELECT version()` as a string (proves a live
  connection).

Smoke test (run from the repo with the venv that has `psycopg2-binary`):

```bash
SKYDASH_DATABASE_URL=$(grep '^SKYDASH_DATABASE_URL=' /home/volodro/terraform/.env \
                       | head -1 | cut -d= -f2-) \
  /home/volodro/skydash/venv/bin/python skydash/db.py
# healthcheck: PostgreSQL 16.14 (Ubuntu ...)
```

## Python dependency

`psycopg2-binary==2.9.12` was installed into `/home/volodro/skydash/venv`
(the venv that runs the Flask app), so `import psycopg2` works in the deployed
environment.

## Notes / handoff

- The running Flask `skydash.service` was **NOT** restarted as part of this
  work — that is the app-deployment teammate's job. The DB, Redis, module, and
  dependency are all in place and verified independently.
- No existing data was modified; the `skydash` DB was created fresh and only
  the idempotent meta table is added by `ensure_schema()`.
