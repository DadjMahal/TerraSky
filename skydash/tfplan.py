"""Read-only Terraform plan parser (§102-104).

Parses the JSON output of ``terraform show -json plan`` into a structured
diff that the UI can render without executing any Terraform commands.

The parser is intentionally pure-stdlib and operates on an in-memory dict
(or a file path) so it can be unit-tested with a fixture without running
Terraform.
"""
from __future__ import annotations

import json
import os
from typing import Any


def parse_plan(plan: dict | str | os.PathLike) -> dict[str, Any]:
    """Parse a Terraform plan JSON document into a structured diff.

    Args:
        plan: Either a parsed dict (from ``json.loads``) or a path/PathLike
              to a JSON file produced by ``terraform show -json plan``.

    Returns:
        ``{
            "available": bool,
            "format_version": str,
            "terraform_version": str,
            "summary": {"create": n, "update": n, "delete": n, "noop": n, "total": n},
            "resource_changes": [{"address", "type", "name", "action", "before", "after"}],
        }``
        On error, ``{"available": False, "error": str}``.
    """
    if isinstance(plan, (str, os.PathLike)):
        try:
            with open(plan, "r") as f:
                plan = json.load(f)
        except Exception as exc:
            return {"available": False, "error": f"failed to read plan: {exc}"}

    if not isinstance(plan, dict):
        return {"available": False, "error": "plan is not a JSON object"}

    changes = plan.get("resource_changes") or []
    summary = {"create": 0, "update": 0, "delete": 0, "noop": 0, "total": len(changes)}
    parsed_changes = []

    for ch in changes:
        action_list = (ch.get("change") or {}).get("actions") or []
        # Terraform reports actions as a list; pick the dominant one.
        if "create" in action_list:
            action = "create"
        elif "delete" in action_list:
            action = "delete"
        elif "update" in action_list:
            action = "update"
        elif "no-op" in action_list or action_list == [] or (len(action_list) == 1 and action_list[0] == "no-op"):
            action = "noop"
        else:
            action = action_list[0] if action_list else "unknown"
        summary[action] = summary.get(action, 0) + 1

        parsed_changes.append({
            "address": ch.get("address", ""),
            "type": ch.get("type", ""),
            "name": ch.get("name", ""),
            "action": action,
            "before": ch.get("change", {}).get("before", {}),
            "after": ch.get("change", {}).get("after", {}),
        })

    return {
        "available": True,
        "format_version": plan.get("format_version", ""),
        "terraform_version": plan.get("terraform_version", ""),
        "summary": summary,
        "resource_changes": parsed_changes,
    }


def parse_plan_file(path: str) -> dict[str, Any]:
    """Convenience wrapper: read a JSON file and parse it as a plan."""
    return parse_plan(path)
