"""Global inventory + search (§57, §59).

A flat, indexed view over the static inventory (instances) with a case-
insensitive substring search across all user-facing fields, plus provider /
status filters. Pure stdlib — unit-testable without Flask or cloud SDKs.
"""
from __future__ import annotations

from typing import Any


def build_index(instances: list) -> list[dict[str, Any]]:
    """Index instances: include a searchable ``_haystack`` field."""
    rows = []
    for i in instances:
        tags = " ".join(f"{k}:{v}" for k, v in (getattr(i, "tags", None) or {}).items())
        row = {
            "slug": getattr(i, "slug", ""),
            "name": getattr(i, "name", "") or "",
            "provider": getattr(i, "provider", ""),
            "region": getattr(i, "region", "") or "",
            "instance_type": getattr(i, "instance_type", "") or "",
            "status": getattr(i, "status", "") or "",
            "tags": getattr(i, "tags", None) or {},
        }
        row["_haystack"] = " ".join(str(v).lower() for v in
                                    [row["slug"], row["name"], row["provider"],
                                     row["region"], row["instance_type"], row["status"], tags])
        rows.append(row)
    return rows


def search(index: list[dict], query: str = "", provider: str | None = None,
           status: str | None = None) -> list[dict]:
    """Case-insensitive substring search + optional provider/status filters."""
    q = (query or "").strip().lower()
    out = []
    for row in index:
        if q and q not in row["_haystack"]:
            continue
        if provider and row["provider"] != provider:
            continue
        if status and row["status"].lower() != status.lower():
            continue
        out.append({k: v for k, v in row.items() if not k.startswith("_")})
    return out


def summarize(index: list[dict]) -> dict:
    by_provider: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for row in index:
        by_provider[row["provider"]] = by_provider.get(row["provider"], 0) + 1
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
    return {"total": len(index), "by_provider": by_provider, "by_status": by_status}
