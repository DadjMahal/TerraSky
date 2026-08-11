"""Plugin architecture (§72-73): registry + permission declarations.

Plugins declare the permissions they need up-front (least-privilege). The
registry provides register/get/list; :func:`enforce` gates an action against
the plugin's granted permissions so no plugin silently gains capabilities it
did not declare.

Importing this package registers the built-in example plugin (status-reader)
automatically, and ``from plugins.example_status import ...`` is also valid.
"""
from __future__ import annotations

from typing import Any


class Plugin:
    name: str = ""
    kind: str = "generic"  # provider|monitoring|deployment|backup|notification|billing|auth|secret|storage
    permissions: tuple[str, ...] = tuple()

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "permissions": list(self.permissions)}


_registry: dict[str, Plugin] = {}


def register(plugin: Plugin) -> Plugin:
    if not plugin.name:
        raise ValueError("plugin must declare a name")
    _registry[plugin.name] = plugin
    return plugin


def get(name: str) -> Plugin | None:
    return _registry.get(name)


def list_plugins() -> list[dict]:
    return [p.describe() for p in _registry.values()]


def enforce(plugin: Plugin, action: str) -> bool:
    """True when the plugin's declared permissions grant ``action`` (§73)."""
    return "*" in plugin.permissions or action in plugin.permissions


def clear() -> None:
    """Test helper."""
    _registry.clear()


# Register the built-in read-only example plugin at import time.
from plugins.example_status import status_plugin  # noqa: E402

register(status_plugin)
