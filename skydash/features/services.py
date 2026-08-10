"""Service (systemd) management contract (§22)."""
from __future__ import annotations

FEATURE_STATUS = "scaffold"
SPEC_SECTIONS = ["§16", "§22"]

COMMANDS = {
    "list": "systemctl list-units --type=service --no-pager",
    "status": "systemctl status --no-pager <unit>",
    "restart": "sudo systemctl restart <unit>",
    "enable": "sudo systemctl enable --now <unit>",
    "disable": "sudo systemctl disable --now <unit>",
    "start": "sudo systemctl start <unit>",
    "stop": "sudo systemctl stop <unit>",
}


def describe() -> dict:
    return {"feature": "services", "status": FEATURE_STATUS, "spec": SPEC_SECTIONS,
            "commands": COMMANDS,
            "blocked": "requires a deployed agent on the target host"}
