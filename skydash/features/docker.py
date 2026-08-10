"""Docker container management contract (§23)."""
from __future__ import annotations

FEATURE_STATUS = "scaffold"
SPEC_SECTIONS = ["§16", "§23"]

COMMANDS = {
    "containers": "docker ps -a --format '{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}'",
    "images": "docker images --format '{{.Repository}}:{{.Tag}}|{{.ID}}'",
    "start": "docker start <id>",
    "stop": "docker stop <id>",
    "restart": "docker restart <id>",
    "logs": "docker logs --tail 200 <id>",
}


def describe() -> dict:
    return {"feature": "docker", "status": FEATURE_STATUS, "spec": SPEC_SECTIONS,
            "commands": COMMANDS,
            "blocked": "requires docker CLI on target host + deployed agent"}
