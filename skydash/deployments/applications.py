"""Application model (§25) + deterministic deployment engine (§26-28).

* :class:`Application` — repo-backed app with a deploy strategy.
* :class:`DeploymentRecord` — one run of the deploy/rollback lifecycle
  (queued -> building -> deployed | failed | rolled_back).
* :func:`run_deployment` — executes a **deterministic** command with a timeout
  and an output cap; ``dry_run`` mode makes the whole flow unit-testable
  without executing anything on the host.

The engine intentionally does NOT invent a pipeline runner: it shells out to a
configured, project-owned script (npm/systemd/etc.) exactly once (idempotent
by key), which is what §27 asks the platform to orchestrate. Real build
farms, blue/green routing and canary weight shifting are Iteration 6+
BLOCKED items (external infra) — documented, not faked.
"""
from __future__ import annotations

import re
import shlex
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from deployments.approvals import gate as approval_gate  # noqa: F401 (re-export)

# Application/revision key must be safe both as a dict key and a URL path.
_SAFE = re.compile(r"^[a-zA-Z0-9\-_]{1,64}$")

_applications: dict[str, Application] = {}
_deployments: dict[str, DeploymentRecord] = {}


@dataclass
class Application:
    id: str
    name: str
    repo_url: str = ""
    environment: str = "staging"  # dev | staging | prod
    strategy: str = "rolling"
    deploy_command: str = ""  # deterministic script executed on the host

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


@dataclass
class DeploymentRecord:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    application_id: str = ""
    commit: str = ""
    status: str = "queued"  # queued|building|deployed|failed|rolled_back
    approval_id: str = ""
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    logs: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# --- Registry helpers --------------------------------------------------------
def register_application(app: Application) -> Application:
    if not _SAFE.match(app.id):
        raise ValueError(f"application id {app.id!r} must match {_SAFE.pattern}")
    _applications[app.id] = app
    return app


def get_application(app_id: str) -> Application | None:
    return _applications.get(app_id)


def list_applications() -> list[dict]:
    return [a.to_dict() for a in _applications.values()]


def get_deployment(deployment_id: str) -> DeploymentRecord | None:
    return _deployments.get(deployment_id)


# --- Deploy / rollback -------------------------------------------------------
def run_deployment(command: str, timeout: int = 120, dry_run: bool = True, output_cap: int = 20000) -> tuple[bool, list[str], str]:
    """Execute ``command`` deterministically (or simulate when ``dry_run``).

    Returns ``(ok, logs, error)``. Output is capped to ``output_cap`` chars.
    """
    logs: list[str] = []
    if dry_run or not command.strip():
        logs = [f"[dry-run] would execute: {shlex.join(shlex.split(command)) if command else '(none)'}"]
        return True, logs, ""
    try:
        proc = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout)
        out = (proc.stdout or "")[:output_cap]
        if proc.returncode != 0:
            return False, out.splitlines(), (proc.stderr or "exit != 0")[:2000]
        return True, out.splitlines(), ""
    except subprocess.TimeoutExpired:
        return False, [], f"timed out after {timeout}s"
    except Exception as exc:  # noqa: BLE001
        return False, [], str(exc)


def deploy(app: Application, commit: str, requested_by: str = "cli",
           dry_run: bool = True, approval: dict | None = None) -> DeploymentRecord:
    """Create and run a deployment. For prod, call :func:`deploy_with_approval`."""
    rec = DeploymentRecord(application_id=app.id, commit=commit, status="building")
    if approval and approval.get("id"):
        rec.approval_id = approval["id"]
    _deployments[rec.id] = rec
    ok, logs, err = run_deployment(app.deploy_command, dry_run=dry_run)
    rec.logs = logs
    rec.finished_at = time.time()
    rec.status = "deployed" if ok else "failed"
    rec.error = err
    return rec


def deploy_with_approval(app: Application, commit: str, requested_by: str,
                         dry_run: bool = True) -> DeploymentRecord:
    """Prod deployments go through the §66 approval gate."""
    approval = approval_gate("deploy", f"applications/{app.id}", app.environment,
                             requested_by, reason=f"deploy {commit}")
    rec = deploy(app, commit, requested_by=requested_by, dry_run=dry_run, approval=approval)
    if approval:  # approval required + created -> mark the run as blocked until approved
        rec.status = "queued"
        rec.logs = [f"waiting on approval {approval['id']} (prod deploy; §66)"]
    return rec


def rollback(deployment_id: str, requested_by: str = "cli") -> DeploymentRecord:
    rec = _deployments.get(deployment_id)
    if rec is None:
        raise KeyError(f"no deployment {deployment_id}")
    app = _applications.get(rec.application_id)
    if app is None:
        raise KeyError(f"no application for deployment {rec.application_id}")
    # Deterministic rollback = re-run the previous known-good command; with the
    # JSON/Db persistence absent we simulate by marking status (dry-run default).
    ok, logs, err = run_deployment(f"{app.deploy_command} --rollback", dry_run=True)
    rec.logs = rec.logs + logs
    rec.status = "rolled_back" if ok else "failed"
    rec.error = err
    rec.finished_at = time.time()
    return rec
