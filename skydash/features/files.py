"""File manager contract (§20, §79)."""
from __future__ import annotations

FEATURE_STATUS = "scaffold"
SPEC_SECTIONS = ["§16", "§20", "§79"]

COMMANDS = {
    "list_dir": "ls -la --time-style=long-iso <path>",
    "read_file": "head -c <limit> <path>",
    "write_file": "base64 -d <<< <b64> > <path>",
    "delete_file": "rm -- <path>",
    "stat": "stat --printf='%s %a %U %G %T\\n' <path>",
}

LIMITS = {"max_upload_bytes": 100 * 1024 * 1024, "blocked_extensions": (".sh", ".pyc")}


def describe() -> dict:
    """Return the feature contract (exposed to the API/docs layer)."""
    return {"feature": "files", "status": FEATURE_STATUS, "spec": SPEC_SECTIONS,
            "commands": COMMANDS, "limits": LIMITS,
            "blocked": "requires a deployed agent on the target host"}
