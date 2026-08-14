"""Normalized security-group / firewall data structures and helpers.

Every provider returns a list of *security groups* (AWS Security Groups,
DigitalOcean Cloud Firewalls, OCI Security Lists / NSGs, Azure NSGs, Alibaba
Security Groups) using the same dict shape, so the API endpoint and front-end
(tools/security-groups.js) can render them provider-agnostically while still
exposing provider-specific branding.

Shape (per group):
    {
        "id":   "<provider-local id or name>",
        "name": "<human label>",
        "type": "AWS SecurityGroup" | "DO Cloud Firewall" | "OCI NSG" |
                "OCI SecurityList" | "Azure NSG" | "Alibaba SecurityGroup" |
                "Custom SSH",
        "provider": "<normalized provider key>",
        "inbound": [<rule>, ...],
        "outbound": [<rule>, ...],
    }

Rule shape (inbound/outbound — identical):
    {
        "protocol":  "tcp" | "udp" | "icmp" | "all" | ...,
        "port":      "<port or port-range, e.g. 22 / 8000-9000 / all>",
        "port_from": <int|None>,      # machine-friendly lower bound
        "port_to":   <int|None>,      # machine-friendly upper bound
        "source":    "<cidr / range / sg-id / '0.0.0.0/0'>",
        "direction": "inbound" | "outbound",
        "action":    "allow" | "deny",
        "description": "<optional>",
    }
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "make_rule",
    "normalize_port",
    "make_group",
    "empty_group",
]


# (from, to) inclusive tuples for the human-readable port label.
def normalize_port(port_from: Any, port_to: Any) -> str:
    """Return ``\"8000-9000\"`` (range), ``\"22\"`` (single) or ``\"all\"``."""
    try:
        pf = int(port_from) if port_from is not None else None
        pt = int(port_to) if port_to is not None else None
    except (TypeError, ValueError):
        return "all"
    if pf is None and pt is None:
        return "all"
    if pf == pt:
        return str(pf)
    lo, hi = (pf or 0), (pt or 65535)
    return f"{lo}-{hi}" if lo != hi else str(lo)


def make_rule(
    protocol: str,
    port_from: Any,
    port_to: Any,
    source: str,
    direction: str,
    action: str = "allow",
    description: str = "",
) -> dict:
    """Build a normalized rule dict."""
    return {
        "protocol": (protocol or "all").lower(),
        "port": normalize_port(port_from, port_to),
        "port_from": int(port_from) if str(port_from).isdigit() else None,
        "port_to": int(port_to) if str(port_to).isdigit() else None,
        "source": source or "0.0.0.0/0",
        "direction": direction,
        "action": action,
        "description": description or "",
    }


def make_group(
    group_id: str,
    name: str,
    type_label: str,
    provider: str,
    inbound: list[dict] | None = None,
    outbound: list[dict] | None = None,
) -> dict:
    """Build a normalized group dict."""
    return {
        "id": group_id,
        "name": name or group_id,
        "type": type_label,
        "provider": provider,
        "inbound": inbound or [],
        "outbound": outbound or [],
    }


def empty_group(group_id: str, name: str, type_label: str, provider: str) -> dict:
    """A group with no rules (used when a lookup resolves but has nothing)."""
    return make_group(group_id, name, type_label, provider)
