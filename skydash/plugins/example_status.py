"""Example read-only plugin for the plugin registry (§72)."""
from __future__ import annotations

from . import Plugin


class StatusPlugin(Plugin):
    name = "status-reader"
    kind = "monitoring"
    permissions = ("inventory.read", "status.read")

    def ping(self) -> dict:
        return {"ok": True, "plugin": self.name, "kind": self.kind}


status_plugin = StatusPlugin()
