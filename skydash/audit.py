"""Append-only audit log (§37) persisted to daily JSONL files.

Storage
-------
    skydash/audit_logs/audit_<YYYY-MM-DD>.jsonl   (git-ignored)

Immutability
------------
* By convention: no code path ever rewrites or deletes an audit line;
  :func:`add` only ever appends to the current day's file.
* Tamper-evidence: every record carries ``prev_hash`` = SHA-256 of the
  previous record's canonical JSON serialization, forming a hash chain.
  :func:`verify_chain` recomputes the chain and reports any broken link.

Scope
-----
The spec's append-only audit *table* (§37, domain model AuditLog) requires
the PostgreSQL domain-model DB (Iteration 10) — **BLOCKED**. Until then this
JSONL store is the authoritative audit trail and is searchable via
:func:`query` (filter by action/actor/resource/day) and exposed through the
API governance checklist. External aggregators (syslog/SIEM) are BLOCKED.

Concurrency: single-process Flask, so a :class:`threading.Lock` (plus
``O_APPEND`` semantics) is sufficient.
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
import threading
from datetime import date, datetime
from typing import Any

# Directory holding the daily JSONL files (git-ignored). Override via env for
# tests / non-standard installs.
AUDIT_DIR = os.environ.get("SKYDASH_AUDIT_DIR", "")
if not AUDIT_DIR:
    AUDIT_DIR = os.path.join(os.path.dirname(__file__), "audit_logs")

_SEQ_CACHE: dict[str, tuple[int, str]] = {}  # day -> (last seq, last hash)
_LOCK = threading.Lock()
def _today() -> str:
    return date.today().isoformat()


def _filename(day: str) -> str:
    os.makedirs(AUDIT_DIR, exist_ok=True)
    return os.path.join(AUDIT_DIR, f"audit_{day}.jsonl")


def _canonical(record: dict) -> bytes:
    """Deterministic JSON serialization for hashing (sorted, compact)."""
    return json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _to_serializable(value: Any) -> Any:
    """Coerce non-JSON values (datetimes, sets, bytes) for the log line."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


def _read_tail(day: str) -> tuple[int, str]:
    """Scan a day file for (last_seq, last_hash) — used to seed the chain.

    Runs once per file per process; subsequent appends chain from memory.
    """
    path = _filename(day)
    last_seq, last_hash = 0, hashlib.sha256(b"skydash-audit-genesis").hexdigest()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                last_seq = int(rec.get("seq", 0))
                last_hash = hashlib.sha256(_canonical(rec)).hexdigest()
    return last_seq, last_hash
def add(
    actor: str,
    action: str,
    resource: str,
    detail: dict | None = None,
    ip: str | None = None,
    outcome: str = "success",
) -> dict:
    """Append one immutable audit record and return it.

    Args:
        actor:    username (or "anonymous"/"system") performing the action.
        action:   dotted action id, e.g. ``server.stop`` or ``settings.update``.
        resource: resource identifier, e.g. ``instances/aws-hermes`` or the
                  HTTP path for routes.
        detail:   optional JSON-serializable context (params, before/after).
        ip:       client address (best effort; proxied IPs need
                  ``ProxyFix``/trusted headers — out of scope here).
        outcome:  ``success`` | ``error`` | ``denied``.

    Returns the record dict as written (including ``seq`` and ``prev_hash``).
    """
    day = _today()
    with _LOCK:
        if day not in _SEQ_CACHE:
            _SEQ_CACHE[day] = _read_tail(day)
        last_seq, last_hash = _SEQ_CACHE[day]
        seq = last_seq + 1
        record: dict = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "seq": seq,
            "actor": str(actor or "anonymous"),
            "action": str(action),
            "resource": str(resource or ""),
            "outcome": outcome,
            "ip": ip,
            "prev_hash": last_hash,
        }
        if detail is not None:
            record["detail"] = detail
        record["hash"] = hashlib.sha256(_canonical(record)).hexdigest()
        with open(_filename(day), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=_to_serializable) + "\n")
            fh.flush()
        _SEQ_CACHE[day] = (seq, record["hash"])
        return record


def _iter_records(path: str):
    """Yield parsed records from one JSONL file (oldest first)."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # Partial/corrupt trailing line (crash mid-write): skip, do
                # not let one bad line hide the rest of the audit trail.
                continue


def _list_days() -> list[str]:
    """Sorted day labels present in the audit directory."""
    if not os.path.isdir(AUDIT_DIR):
        return []
    return sorted(
        f[6:-6]
        for f in os.listdir(AUDIT_DIR)
        if f.startswith("audit_") and f.endswith(".jsonl")
    )
def query(
    day: str | None = None,
    action: str | None = None,
    actor: str | None = None,
    resource: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Search the audit trail.

    Returns up to ``limit`` records (newest first) matching all given
    filters. ``day`` defaults to today; pass ``"*"`` to search every file in
    the audit directory — useful for forensics/reporting.
    """
    if day is None:
        day = _today()
    days = [day] if day != "*" else _list_days()
    records: list[dict] = []
    for d in days:
        for rec in _iter_records(_filename(d)):
            if action and rec.get("action") != action:
                continue
            if actor and rec.get("actor") != actor:
                continue
            if resource and rec.get("resource") != resource:
                continue
            records.append(rec)
    records.sort(key=lambda r: (r.get("ts", ""), r.get("seq", 0)), reverse=True)
    return records[:limit]


def verify_chain(day: str | None = None) -> dict:
    """Recompute and verify the hash chain for one day (or ``"*"`` for all).

    Returns ``{"ok", "checked", "broken", "first_break"}``. A tampered or
    hand-edited record breaks the chain it feeds.
    """
    if day is None:
        day = _today()
    days = [day] if day != "*" else _list_days()
    checked = broken = 0
    first_break = ""
    genesis = hashlib.sha256(b"skydash-audit-genesis").hexdigest()
    for d in days:
        prev_hash = genesis
        for rec in _iter_records(_filename(d)):
            checked += 1
            if rec.get("prev_hash") != prev_hash:
                broken += 1
                first_break = first_break or f"{d}:{rec.get('seq')}"
            payload = dict(rec)
            payload.pop("hash", None)
            prev_hash = hashlib.sha256(_canonical(payload)).hexdigest()
    return {
        "ok": broken == 0,
        "checked": checked,
        "broken": broken,
        "first_break": first_break,
    }


def audited(action: str | None = None, resource: str | None = None):
    """Decorator: record every call of a view in the audit trail.

    Additive and non-blocking: the view runs normally; afterwards (or on
    exception) a record is appended capturing actor, action, resource,
    outcome and (status-derived) result. ``action`` defaults to the view
    function name, ``resource`` to the request path; either may also be a
    callable receiving ``(*args, **kwargs)`` for dynamic values (e.g. the
    route's slug).
    """

    def decorator(view):
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            from flask import request, session

            from auth import SESSION_KEY

            actor = session.get(SESSION_KEY, "anonymous")
            act_base = action if action is not None else view.__name__
            res_base = resource if resource is not None else request.path
            act = act_base(*args, **kwargs) if callable(act_base) else act_base
            res = res_base(*args, **kwargs) if callable(res_base) else res_base
            try:
                result = view(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - record then re-raise
                add(
                    actor,
                    act,
                    res,
                    detail={"error": str(exc), "args": dict(kwargs)},
                    ip=request.remote_addr,
                    outcome="error",
                )
                raise
            status = _status_of(result)
            outcome = "success" if 200 <= status < 400 else "error"
            add(
                actor,
                act,
                res,
                detail={"status": status, "args": dict(kwargs)},
                ip=request.remote_addr,
                outcome=outcome,
            )
            return result

        return wrapper

    return decorator


def _status_of(result) -> int:
    """Extract an HTTP status from a Flask view result without importing Flask."""
    if isinstance(result, tuple):
        for part in result:
            if isinstance(part, int):
                return part
    status = getattr(result, "status_code", None)
    return int(status) if isinstance(status, int) else 200