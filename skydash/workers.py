"""Ephemeral worker + command-execution security (§74-75).

:func:`run_isolated` shells out with a hard timeout, an output cap, an
optional command allowlist and an optional approval gate. Real container-level
isolation (sandbox VM/runtime) is a production-hardening item (§74, Iter 10) —
here we implement the *security envelope* a remote invocation must pass.
"""
from __future__ import annotations

import subprocess
import time
from typing import Any

# Commands that a scoped agent/plugin may run without extra approval (§75).
SAFE_COMMANDS = ("ls", "df", "free", "uptime", "ps", "journalctl", "systemctl status", "hostname")


def run_isolated(command: str, timeout: int = 30, output_cap: int = 10000,
                 allowlist: tuple[str, ...] = SAFE_COMMANDS,
                 require_approval: bool = False) -> dict[str, Any]:
    """Execute a command under the security envelope.

    Returns ``{"ok", "output", "error", "code", "elapsed"}``. A matching
    command prefix is required when ``allowlist`` is non-empty; ``*`` disables
    the allowlist (unsafe, for explicit workflows only).
    """
    started = time.time()
    if require_approval:
        return {"ok": False, "output": "", "error": "approval required (§66/§75)", "code": "NEEDS_APPROVAL", "elapsed": round(time.time() - started, 3)}
    if allowlist and "*" not in allowlist:
        head = command.strip()
        if not any(head.startswith(c) for c in allowlist):
            return {"ok": False, "output": "", "error": f"command not in allowlist: {head.split()[0] if head else ''}", "code": "NOT_ALLOWED", "elapsed": round(time.time() - started, 3)}
    try:
        proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        out = (proc.stdout or "")[:output_cap]
        return {"ok": proc.returncode == 0, "output": out, "error": (proc.stderr or "")[:2000],
                "code": "OK" if proc.returncode == 0 else f"EXIT_{proc.returncode}",
                "elapsed": round(time.time() - started, 3)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "", "error": f"timed out after {timeout}s", "code": "TIMEOUT", "elapsed": round(time.time() - started, 3)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "output": "", "error": str(exc), "code": "INTERNAL", "elapsed": round(time.time() - started, 3)}
