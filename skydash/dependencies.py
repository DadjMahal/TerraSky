"""Resource relationships (§88): graph derived from instance tags.

Sources of edges (both additive and cheap):
* ``depends_on`` / ``dependency`` tag — comma-separated slugs this instance
  depends on (explicit edges).
* ``app`` tag — instances sharing an app tag are grouped as a cluster
  (implicit edges, labelled ``app:<name>``).

The topology the dashboard renders (``static/js/topology.js``) consumes this
graph through ``GET /api/v1/topology``.
"""
from __future__ import annotations

from typing import Any

DEPENDS_TAG_KEYS = ("depends_on", "dependency")
APP_TAG_KEY = "app"


def _tags(inst) -> dict:
    raw = getattr(inst, "tags", None) or {}
    return {str(k).lower(): str(v) for k, v in raw.items()}


def _parse_slugs(value: str) -> list[str]:
    return [s.strip() for s in value.split(",") if s.strip()]


def build_graph(instances: list) -> dict[str, dict]:
    """Return ``{slug: {"dependencies": [...], "dependents": [...], "app": str|None}}``."""
    graph: dict[str, dict] = {}
    for inst in instances:
        graph.setdefault(inst.slug, {"dependencies": [], "dependents": [], "app": None})

    by_slug = {inst.slug: inst for inst in instances}

    # Explicit depends_on edges
    for inst in instances:
        tags = _tags(inst)
        app = None
        for key in DEPENDS_TAG_KEYS:
            if tags.get(key):
                for dep in _parse_slugs(tags[key]):
                    if dep in graph and dep != inst.slug:
                        if dep not in graph[inst.slug]["dependencies"]:
                            graph[inst.slug]["dependencies"].append(dep)
                        if inst.slug not in graph[dep]["dependents"]:
                            graph[dep]["dependents"].append(inst.slug)
        app = tags.get(APP_TAG_KEY) or app
        graph[inst.slug]["app"] = app

    # Implicit cluster edges via shared app tag
    apps: dict[str, list[str]] = {}
    for slug, node in graph.items():
        if node.get("app"):
            apps.setdefault(node["app"], []).append(slug)
    for members in apps.values():
        if len(members) > 1:
            for m in members:
                graph[m].setdefault("cluster", f"app:{_norm_app(members[0])}")
    return graph


def _norm_app(app: str) -> str:
    return app.lower().replace(" ", "-")


def dependencies(graph: dict, slug: str) -> list[str]:
    return list(graph.get(slug, {}).get("dependencies", []))


def dependents(graph: dict, slug: str) -> list[str]:
    return list(graph.get(slug, {}).get("dependents", []))


def as_topology(graph: dict) -> list[dict[str, Any]]:
    """Flat, JSON-friendly list of nodes+edges for the UI graph renderer."""
    nodes = [{"id": slug, "app": node.get("app"), "cluster": node.get("cluster")}
             for slug, node in graph.items()]
    edges = []
    for slug, node in graph.items():
        for dep in node["dependencies"]:
            edges.append({"source": slug, "target": dep})
    return {"nodes": nodes, "edges": edges}
