"""Runtime tests for Project/Environment domain entities (§6.1, §105).

Pure stdlib — runs without Flask or cloud SDKs.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_project_crud():
    import projects

    projects.clear()
    p = projects.register_project(name="Web Services", slug="web-svc")
    assert p.id and p.slug == "web-svc" and p.name == "Web Services"
    assert projects.get_project("web-svc") is p
    assert len(projects.list_projects()) == 1
    assert projects.list_projects()[0]["slug"] == "web-svc"
    assert projects.delete_project("web-svc") is True
    assert projects.get_project("web-svc") is None
    assert len(projects.list_projects()) == 0


def test_project_duplicate_slug_rejected():
    import projects

    projects.clear()
    projects.register_project(name="A", slug="shared")
    try:
        projects.register_project(name="B", slug="shared")
    except ValueError:
        pass
    else:
        assert False, "duplicate slug should raise ValueError"
    assert len(projects.list_projects()) == 1


def test_environment_crud_and_listing_by_project():
    import projects

    projects.clear()
    projects.register_project(name="Platform", slug="platform")
    dev = projects.register_environment(name="dev", slug="platform-dev",
                                        project_slug="platform", kind="dev")
    prod = projects.register_environment(name="prod", slug="platform-prod",
                                          project_slug="platform", kind="prod",
                                          protection_reason="customer data")
    assert dev.kind == "dev" and prod.kind == "prod"
    assert prod.protection_reason == "customer data"
    envs = projects.list_environments("platform")
    assert len(envs) == 2
    assert {e["slug"] for e in envs} == {"platform-dev", "platform-prod"}
    # project_id links to the Project's UUID id, not the slug
    projs = projects.list_projects()
    assert projs[0]["id"] == dev.project_id == prod.project_id


def test_environment_invalid_kind_rejected():
    import projects

    projects.clear()
    projects.register_project(name="P", slug="p")
    try:
        projects.register_environment(name="x", slug="x", project_slug="p", kind="qa")
    except ValueError:
        pass
    else:
        assert False, "invalid kind should raise ValueError"


def test_environment_under_missing_project_rejected():
    import projects

    projects.clear()
    try:
        projects.register_environment(name="x", slug="x", project_slug="nope")
    except ValueError:
        pass
    else:
        assert False, "missing project should raise ValueError"


def test_delete_project_blocks_when_environments_exist():
    import projects

    projects.clear()
    projects.register_project(name="P", slug="p")
    projects.register_environment(name="dev", slug="p-dev", project_slug="p")
    try:
        projects.delete_project("p")
    except ValueError:
        pass
    else:
        assert False, "should not delete project with environments"
    assert projects.get_project("p") is not None


def test_instance_linking():
    import projects

    projects.clear()
    projects.register_project(name="P", slug="p")
    projects.register_environment(name="dev", slug="p-dev", project_slug="p")
    assert projects.link_instance("p-dev", "aws-hermes") is True
    assert projects.link_instance("p-dev", "aws-hermes") is True  # idempotent
    assert projects.instances_in("p-dev") == ["aws-hermes"]
    assert projects.instances_in("missing") == []


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception as exc:
                failures += 1
                print(f"FAIL  {name}: {exc}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
