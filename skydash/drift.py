"""Drift detection (§15): desired (terraform.tfstate / static inventory) vs
the live state reported by each provider.

The pure comparison lives here and is unit-testable without any cloud creds;
routing a live check for a provider whose SDK/credentials are unavailable
yields an explicit ``unverifiable`` result instead of guessing.
"""
from __future__ import annotations

from typing import Any

from models import STATUS_ERROR, STATUS_STOPPED, STATUS_UNKNOWN
from providers.registry import get_provider


def _norm(status: str) -> str:
    return (status or "").strip().lower()


def _status_class(status: str) -> str:
    """Bucket raw status strings into running/stopped/other for comparison."""
    s = _norm(status)
    if s in ("running", "active", "started", "ok"):
        return "running"
    if s == "stopped":
        return "stopped"
    return "other"


def compare(desired_status: str, live_status: str) -> dict[str, Any]:
    """Compare one instance: desired (state file) vs live (provider).

    Returns ``{"drifted": bool, "live_state": str, "note": str}``.
    Live 'unknown'/'error' (failed fetch, not a real state change) is reported
    as *unverifiable* rather than drifted — avoids false positives.
    """
    live = _norm(live_status)
    if live in _norm(STATUS_UNKNOWN) or live in _norm(STATUS_ERROR) or live in ("", "unknown", "error"):
        return {"drifted": False, "live_state": live or "unknown", "note": "unverifiable: provider fetch did not return a usable state"}
    drifted = _status_class(desired_status) != _status_class(live)
    return {"drifted": drifted, "live_state": live,
            "note": "desired/live state class mismatch" if drifted else "in sync"}


def detect_instances(instances: list) -> list[dict[str, Any]]:
    """Run drift detection over the desired inventory.

    Providers that are unavailable (no credentials/SDK) mark every instance
    ``unverifiable`` — that is the honest, graceful-degradation behavior.
    """
    results = []
    for inst in instances:
        provider = get_provider(inst.provider)
        if provider is None or not provider.available():
            results.append({
                "slug": inst.slug, "name": inst.name, "provider": inst.provider,
                "desired": inst.status, "live": "unverifiable", "drifted": False,
                "note": f"provider '{inst.provider}' unavailable in this environment",
            })
            continue
        try:
            live, err, _pub, _pri = provider.get_status(inst)
            comp = compare(inst.status, live)
            results.append({
                "slug": inst.slug, "name": inst.name, "provider": inst.provider,
                "desired": inst.status, "live": comp["live_state"],
                "drifted": comp["drifted"], "note": comp["note"] if not err else err,
            })
        except Exception as exc:  # noqa: BLE001 - one bad fetch must not abort the sweep
            results.append({
                "slug": inst.slug, "name": inst.name, "provider": inst.provider,
                "desired": inst.status, "live": "unverifiable", "drifted": False,
                "note": f"error: {exc}",
            })
    return results


def summarize(results: list[dict]) -> dict:
    counts = {"in_sync": 0, "drifted": 0, "unverifiable": 0}
    for r in results:
        if r.get("drifted"):
            counts["drifted"] += 1
        elif r.get("note", "").startswith("unverifiable") or r.get("live") == "unverifiable":
            counts["unverifiable"] += 1
        else:
            counts["in_sync"] += 1
    counts["total"] = len(results)
    return counts
