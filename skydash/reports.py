"""Report generation (§92-93): CSV/JSON from inventory + cost records.

Pure functions — no I/O, so the exact bytes are unit-testable.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from billing.model import CostRecord


def inventory_csv(index: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["slug", "name", "provider", "region", "instance_type", "status"])
    for r in index:
        writer.writerow([r["slug"], r["name"], r["provider"], r["region"],
                         r["instance_type"], r["status"]])
    return buf.getvalue()


def costs_csv(records: list[CostRecord]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["provider", "resource_slug", "service", "region", "amount", "currency", "project"])
    for r in records:
        writer.writerow([r.provider, r.resource_slug, r.service, r.region, r.amount, r.currency, r.project or ""])
    return buf.getvalue()


def inventory_json(index: list[dict]) -> dict[str, Any]:
    return {"items": index, "total": len(index)}
