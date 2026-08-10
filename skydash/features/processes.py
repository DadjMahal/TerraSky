"""Process manager contract (§21)."""
from __future__ import annotations

FEATURE_STATUS = "scaffold"
SPEC_SECTIONS = ["§16", "§21"]

COMMANDS = {
    "list": "ps -eo pid,ppid,user,%cpu,%mem,rss,stat,etime,command --sort=-%cpu",
    "kill": "kill -<signal> <pid>",
    "usage": "ps -p <pid> -o pid,%cpu,%mem,rss,vsz,etime,cmd",
}


def describe() -> dict:
    return {"feature": "processes", "status": FEATURE_STATUS, "spec": SPEC_SECTIONS,
            "commands": COMMANDS,
            "blocked": "requires a deployed agent on the target host"}
