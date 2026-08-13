"""Project + Environment domain entities (Iteration 8, §6.1, §105).

In-memory registry with CRUD helpers. Model hierarchy target:
Organization → Projects → Environments → Resources (see docs/domain-model.md).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

VALID_KINDS = ("dev", "stage", "prod")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Environment:
    """A deployment environment (dev/stage/prod) inside a Project."""
    id: str
    name: str
    slug: str
    project_id: str
    kind: str
    protection_reason: Optional[str] = None
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "project_id": self.project_id,
            "kind": self.kind,
            "created_at": self.created_at,
        }
        if self.protection_reason:
            d["protection_reason"] = self.protection_reason
        return d


@dataclass
class Project:
    """Top-level grouping entity: 1:N Environments, Teams."""
    id: str
    name: str
    slug: str
    org_id: str = "default"
    tags: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "org_id": self.org_id,
            "tags": self.tags,
            "created_at": self.created_at,
        }


# --- In-memory registry -------------------------------------------------------

_projects: dict[str, Project] = {}          # slug -> Project
_environments: dict[str, Environment] = {}  # slug -> Environment
_links: dict[str, list[str]] = {}           # env slug -> [instance slug]


def clear() -> None:
    """Reset all in-memory state (used by tests and on restart)."""
    _projects.clear()
    _environments.clear()
    _links.clear()


def register_project(name: str, slug: str, org_id: str = "default",
                     tags: dict[str, str] | None = None) -> Project:
    """Create a project; raises ValueError on duplicate slug."""
    if not name or not slug:
        raise ValueError("name and slug are required")
    if slug in _projects:
        raise ValueError(f"project slug already exists: {slug}")
    proj = Project(id=str(uuid.uuid4()), name=name, slug=slug,
                   org_id=org_id, tags=tags or {})
    _projects[slug] = proj
    _links.setdefault(slug, [])
    return proj


def get_project(slug: str) -> Project | None:
    return _projects.get(slug)


def list_projects() -> list[dict[str, Any]]:
    return [p.to_dict() for p in _projects.values()]


def delete_project(slug: str) -> bool:
    """Delete a project; raises ValueError if it still has environments."""
    if slug not in _projects:
        return False
    if any(e.project_id == _projects[slug].id for e in _environments.values()):
        raise ValueError("cannot delete project with environments")
    _projects.pop(slug)
    _links.pop(slug, None)
    return True


def register_environment(name: str, slug: str, project_slug: str,
                         kind: str = "dev", protection_reason: str | None = None) -> Environment:
    """Create an environment under a project; raises ValueError if project
    is missing, slug is taken, or kind is not dev/stage/prod."""
    if kind not in VALID_KINDS:
        raise ValueError(f"kind must be one of {', '.join(VALID_KINDS)}")
    proj = _projects.get(project_slug)
    if proj is None:
        raise ValueError(f"project not found: {project_slug}")
    if slug in _environments:
        raise ValueError(f"environment slug already exists: {slug}")
    env = Environment(id=str(uuid.uuid4()), name=name, slug=slug,
                      project_id=proj.id, kind=kind, protection_reason=protection_reason)
    _environments[slug] = env
    _links.setdefault(project_slug, [])
    return env


def list_environments(project_slug: str | None = None) -> list[dict[str, Any]]:
    """List all environments, optionally filtered by project slug."""
    return [e.to_dict() for e in _environments.values()
            if project_slug is None or e.project_id == _projects[project_slug].id]


def link_instance(env_slug: str, instance_slug: str) -> bool:
    """Link an instance to an environment (idempotent)."""
    if env_slug not in _environments:
        return False
    proj_slug = next((s for s, e in _environments.items() if e.project_id == _environments[env_slug].project_id), None)
    bucket = _links.setdefault(env_slug, [])
    if proj_slug is not None:
        _links.setdefault(proj_slug, [])
    if instance_slug not in bucket:
        bucket.append(instance_slug)
    return True


def instances_in(env_slug: str) -> list[str]:
    """Return instance slugs linked to an environment."""
    return list(_links.get(env_slug, []))
