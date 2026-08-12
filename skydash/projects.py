"""Project & Environment domain entities (§6.1, §105).

In-process registry following the same pattern as ``deployments/applications.py``.
Persistence to PostgreSQL (§119, §127) is targeted in Iteration 10; for now the
registry lives in-process, seeded from config_store overrides or tfstate tags.

The hierarchy is: Organization → Projects → Environments → Resources (instances).
Each Environment carries a ``kind`` (dev/stage/prod) and an optional
``protection_reason`` that the prod-shield (§67-68) respects before destructive
actions.
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

# Slug / ID safety: same convention as deployments/applications.py
_SAFE = re.compile(r"^[a-zA-Z0-9\-_]{1,64}$")

#: Allowed environment kinds (§6.1)
ENV_KINDS: tuple[str, ...] = ("dev", "stage", "prod")

#: Default organization (single-tenant until Iter 9)
DEFAULT_ORG_ID = "default"

# --- Registries (in-process, like applications.py) ---------------------------
_projects: dict[str, "Project"] = {}
_environments: dict[str, "Environment"] = {}
_instance_links: dict[str, list[str]] = {}  # env_slug -> [instance_slug, ...]


@dataclass
class Project:
    """A logical grouping of environments (§6.1)."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    slug: str = ""
    org_id: str = DEFAULT_ORG_ID
    tags: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Environment:
    """A deployment target within a project (§6.1, §105)."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    slug: str = ""
    project_id: str = ""
    kind: str = "dev"  # dev | stage | prod
    protection_reason: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# --- Project registry helpers --------------------------------------------------
def _validate_slug(slug: str) -> str:
    if not slug or not _SAFE.match(slug):
        raise ValueError(f"slug {slug!r} must match {_SAFE.pattern}")
    return slug


def register_project(name: str, slug: str, org_id: str = DEFAULT_ORG_ID,
                     tags: dict | None = None) -> Project:
    """Create and store a Project, keyed by slug."""
    _validate_slug(slug)
    if slug in _projects:
        raise ValueError(f"project {slug!r} already exists")
    proj = Project(name=name, slug=slug, org_id=org_id, tags=tags or {})
    _projects[slug] = proj
    return proj


def get_project(slug: str) -> Project | None:
    return _projects.get(slug)


def list_projects() -> list[dict]:
    return [p.to_dict() for p in _projects.values()]


def delete_project(slug: str) -> bool:
    """Remove a project and all its environments. Fails if environments exist."""
    if slug not in _projects:
        return False
    if any(e.project_id == _projects[slug].id for e in _environments.values()):
        raise ValueError(f"cannot delete project {slug!r}: environments still attached")
    del _projects[slug]
    return True


# --- Environment registry helpers ----------------------------------------------
def register_environment(name: str, slug: str, project_slug: str,
                         kind: str = "dev", protection_reason: str = "") -> Environment:
    """Create and store an Environment under a project."""
    _validate_slug(slug)
    proj = _projects.get(project_slug)
    if proj is None:
        raise ValueError(f"project {project_slug!r} does not exist")
    if kind not in ENV_KINDS:
        raise ValueError(f"kind must be one of {ENV_KINDS}")
    if slug in _environments:
        raise ValueError(f"environment {slug!r} already exists")
    env = Environment(name=name, slug=slug, project_id=proj.id,
                      kind=kind, protection_reason=protection_reason)
    _environments[slug] = env
    _instance_links[slug] = []
    return env


def get_environment(slug: str) -> Environment | None:
    return _environments.get(slug)


def list_environments(project_slug: str | None = None) -> list[dict]:
    envs = _environments.values()
    if project_slug is not None:
        proj = _projects.get(project_slug)
        if proj is None:
            return []
        envs = [e for e in envs if e.project_id == proj.id]
    return [e.to_dict() for e in envs]


def delete_environment(slug: str) -> bool:
    if slug not in _environments:
        return False
    del _environments[slug]
    _instance_links.pop(slug, None)
    return True


# --- Instance linking ----------------------------------------------------------
def link_instance(env_slug: str, instance_slug: str) -> bool:
    """Attach an instance slug to an environment."""
    if env_slug not in _environments:
        return False
    links = _instance_links.setdefault(env_slug, [])
    if instance_slug not in links:
        links.append(instance_slug)
    return True


def instances_in(env_slug: str) -> list[str]:
    return list(_instance_links.get(env_slug, []))


def clear():
    """Reset all registries (used in tests)."""
    _projects.clear()
    _environments.clear()
    _instance_links.clear()
