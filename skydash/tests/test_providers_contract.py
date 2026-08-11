"""Provider contract tests (§116) — every adapter MUST satisfy the SDK contract.

Runs without any cloud credentials: it only verifies interface conformance
(methods present, capabilities declared, available() never raises). Live
round-trips need real credentials (deploy) — out of scope here.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from providers.base import CloudProvider  # noqa: E402
from providers.registry import all_providers  # noqa: E402


def test_all_providers_are_cloudprovider_and_declare_capabilities():
    for p in all_providers():
        assert isinstance(p, CloudProvider), f"{p.key} must subclass CloudProvider"
        assert isinstance(p.key, str) and p.key, f"{p} missing .key"
        caps = p.get_capabilities()
        assert isinstance(caps, list) and all(isinstance(c, str) for c in caps), f"{p.key} capabilities invalid"


def test_provider_interface_and_availability_never_raises():
    for p in all_providers():
        for method in ("available", "start_instance", "stop_instance", "get_logs"):
            assert callable(getattr(p, method, None)), f"{p.key} missing {method}"
        # available() must not raise even when no credentials are present
        assert p.available() in (True, False)


def test_start_stop_capabilities_line_up():
    # A provider that declares "start"/"stop" must not be read-only.
    for p in all_providers():
        caps = set(p.get_capabilities())
        assert "stop" not in caps or "start" in caps, f"{p.key}: 'stop' without 'start' is inconsistent"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"FAIL  {name}: {exc}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
