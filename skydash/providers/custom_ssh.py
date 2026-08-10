"""Custom / SSH-only provider (§9, §97) for infrastructure reachable only
over SSH (bare metal, Raspberry Pi, the Hermes agent host, VMs without a cloud
control plane).

Implements :class:`CloudProvider` so the SSH-only machines are managed through
the exact same registry/API as AWS/Azure/Oracle/Alibaba/DigitalOcean — no
provider-specific logic leaks into the Flask layer.

Implementation notes
--------------------
* Reuses the paramiko helpers from ``hermes_agent`` (same keystore/username
  resolution: ``~/.ssh`` key, ``HERMES_SSH_USER``/``HERMES_SSH_KEY`` env).
* ``available()`` is True when paramiko imports and a host can be resolved
  (instance ``public_ip`` or ``HERMES_SSH_HOST`` env var) and the SSH key
  file exists on disk.
* Power control (start/stop) is deliberately NOT offered for SSH-only hosts —
  there is no control plane to do it safely. Reboot/logs/disk are.
"""
from __future__ import annotations

import os

from models import STATUS_ERROR, STATUS_RUNNING, STATUS_UNKNOWN
from providers.base import CloudProvider

try:  # paramiko may be absent (no SSH deps installed) -> provider degrades
    import hermes_agent
except ImportError:  # pragma: no cover
    hermes_agent = None


class CustomSSHProvider(CloudProvider):
    key = "custom_ssh"
    capabilities = (
        "read",
        "reboot",
        "execute_command",
        "service_restart",
        "get_logs",
        "disk",
        "test_connection",
    )

    def available(self) -> bool:
        if hermes_agent is None:  # pragma: no cover - paramiko import guard
            return False
        return bool(self._resolve_host(None)) and self._ssh_key_exists()

    # --- internals ---------------------------------------------------------
    def _ssh_key_exists(self) -> bool:
        try:
            path = hermes_agent._get_ssh_key_path()
        except Exception:  # noqa: BLE001
            return False
        return bool(path) and os.path.exists(path)

    def _resolve_host(self, instance) -> str | None:
        if instance is not None and getattr(instance, "public_ip", None):
            return instance.public_ip
        host = os.environ.get("HERMES_SSH_HOST", "").strip()
        return host or None

    # --- CloudProvider interface ------------------------------------------
    def get_status(self, instance) -> tuple:
        host = self._resolve_host(instance)
        if not host:
            return STATUS_UNKNOWN, "no SSH host resolvable for instance", "", ""
        try:
            res = hermes_agent.test_connection(host)
            ok = bool(res and res.get("ok"))
            return (STATUS_RUNNING if ok else STATUS_ERROR,
                    "" if ok else (res or {}).get("error", "SSH connection failed"),
                    host, "")
        except Exception as exc:  # noqa: BLE001
            return STATUS_ERROR, str(exc), host, ""

    def start_instance(self, instance):  # noqa: D401 - intentionally unsupported
        return False, "custom SSH hosts have no control plane; cannot power on"

    def stop_instance(self, instance):
        return False, "custom SSH hosts have no control plane; reboot instead"

    def reboot(self, instance):
        """Reboot via SSH (``systemctl reboot``). Requires sudo, so primary use
        is the user's own host. Returns (ok, message)."""
        host = self._resolve_host(instance)
        if not host:
            return False, "no SSH host resolvable"
        try:
            client = hermes_agent._ssh_connect(host)
            out = hermes_agent._run_command(client, "sudo /sbin/systemctl reboot", timeout=10)
            ok = out.get("ok", True)  # connection may drop on reboot -> treat as ok
            return ok, out.get("output", "reboot issued")[:200]
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def get_logs(self, instance, log_type: str) -> list:
        host = self._resolve_host(instance)
        if not host:
            return []
        try:
            if log_type == "journal":
                out = hermes_agent._run_command(
                    hermes_agent._ssh_connect(host), "journalctl -n 100 --no-pager", timeout=15)
                return (out.get("output") or "").splitlines()
            data = hermes_agent.fetch_all_logs(host, lines=50)
            if isinstance(data, dict):
                merged = []
                for v in data.values():
                    if isinstance(v, list):
                        merged.extend(v)
                    elif isinstance(v, str):
                        merged.append(v)
                return merged
            return []
        except Exception:  # noqa: BLE001
            return []

    def get_disk(self, instance) -> dict:
        host = self._resolve_host(instance)
        if not host:
            return {"error": "no SSH host"}
        try:
            return hermes_agent.fetch_disk_status(host)
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}


# Single shared instance so the registry can reference it like the others.
custom_ssh_provider = CustomSSHProvider()