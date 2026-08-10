"""Lightweight status-change history store for instance timelines (#15).

Each time a live status is observed for a slug we append a {ts, status} entry to a
JSON file (capped to the last N entries per slug so the file never grows unbounded).
This is intentionally simple — no DB, no indexes — enough to render a horizontal
timeline of recent status transitions on the detail page.
"""
from __future__ import annotations

import json
import os
import time
from threading import Lock

_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "status_history.json")
_MAX_PER_SLUG = 50
_lock = Lock()


def _load() -> dict:
    if not os.path.exists(_HISTORY_FILE):
        return {}
    try:
        with open(_HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict) -> None:
    with open(_HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def record(slug: str, status: str) -> None:
    """Append a status observation for a slug (deduped vs the last entry)."""
    if not slug or not status:
        return
    with _lock:
        data = _load()
        entries = data.get(slug, [])
        if entries and entries[-1].get("status") == status:
            # Same state — just refresh the timestamp of the last entry.
            entries[-1]["ts"] = time.time()
        else:
            entries.append({"ts": time.time(), "status": status})
            if len(entries) > _MAX_PER_SLUG:
                entries = entries[-_MAX_PER_SLUG:]
        data[slug] = entries
        _save(data)


def get_history(slug: str) -> list:
    """Return the chronological status transitions for a slug (oldest→newest)."""
    with _lock:
        return list(_load().get(slug, []))


def recent_events(slugs: list[str], limit: int = 20) -> list:
    """Flatten the latest status transitions across slugs into notifications (§60).

    Each event is ``{"slug", "ts", "status"}``, newest first. Pure function of
    the stored history — unit-testable without any Flask/cloud dependencies.
    """
    events = []
    for slug in slugs:
        for entry in get_history(slug):
            ev = {"slug": slug, "ts": entry.get("ts"), "status": entry.get("status")}
            events.append(ev)
    events.sort(key=lambda e: (e.get("ts") or 0), reverse=True)
    return events[:limit]
