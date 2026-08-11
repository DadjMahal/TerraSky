"""Health monitoring + alert thresholds (§44-46).

Data-driven threshold rules evaluated against instance status and optional
metric percentages. Dispatch (email/webhook) is BLOCKED (no SMTP/webhook
infra); the alerts are queryable via GET /api/v1/alerts.
"""
from __future__ import annotations

from typing import Any

# Rules as data: fnmatch-style action patterns + thresholds.
DEFAULT_RULES: list[dict[str, Any]] = [
    {"id": "AL-001", "match": "*", "field": "status", "eq": "error",
     "severity": "critical", "message": "instance is in error state"},
    {"id": "AL-002", "match": "*", "field": "disk_pct", "gte": 90,
     "severity": "warning", "message": "disk usage above 90%"},
    {"id": "AL-003", "match": "*", "field": "cpu_pct", "gte": 95,
     "severity": "warning", "message": "CPU usage above 95%"},
]


def evaluate_row(instance_status: str, extra: dict | None = None,
                 rules: list[dict] | None = None) -> list[dict]:
    """Evaluate one resource against the rules -> list of matching alerts."""
    extra = extra or {}
    hits = []
    for rule in rules or DEFAULT_RULES:
        field = rule.get("field")
        value = instance_status if field == "status" else extra.get(field)
        if value is None:
            continue
        if "eq" in rule and str(value).lower() != str(rule["eq"]).lower():
            continue
        if "gte" in rule and _num(value) < rule["gte"]:
            continue
        hits.append({"id": rule["id"], "severity": rule["severity"],
                     "message": rule["message"], "value": str(value)})
    return hits


def evaluate_fleet(instances: list, extra_by_slug: dict | None = None) -> list[dict[str, Any]]:
    extra_by_slug = extra_by_slug or {}
    alerts = []
    for i in instances:
        hits = evaluate_row(getattr(i, "status", ""), extra_by_slug.get(getattr(i, "slug", "")))
        for h in hits:
            alerts.append({"slug": getattr(i, "slug", ""), "name": getattr(i, "name", ""),
                           "provider": getattr(i, "provider", ""), **h})
    return alerts


def _num(v) -> float:
    try:
        return float(str(v).replace("%", "").strip())
    except Exception:  # noqa: BLE001
        return float("inf")
