"""Prometheus /metrics text-format exposition for SkyDash (Iteration 10; §45, §82).

This module renders a minimal, dependency-free set of metrics in the Prometheus
text exposition format (version 0.0.4). It is intentionally tiny and uses only
the standard library so Prometheus can scrape SkyDash without any monitoring SDK.

Metric naming follows the Prometheus data model: all metrics are prefixed with
``skydash_`` (namespace = application), use ``_total`` for counters, and expose
provider/region as labels on the per-instance gauge.

Exposed metrics
---------------
``skydash_up`` (gauge)
    Liveness: 1 while this endpoint can render.
``skydash_http_requests_total`` (counter)
    Total HTTP requests handled by the process since start, incremented by the
    ``after_request`` hook registered in :mod:`app`.
``skydash_instances`` (gauge, labels ``provider``)
    Number of managed instances reported by Terraform state, per cloud provider.
    Only providers that currently have instances are emitted.
"""

from __future__ import annotations

import collections
import threading
import time

# --- Request counter (fed by the after_request hook in app.py) --------------

_requests_total: int = 0
_requests_lock = threading.Lock()
_process_start = time.time()


def count_request() -> None:
    """Increment the total-request counter. Called from an ``after_request`` hook."""
    global _requests_total
    with _requests_lock:
        _requests_total += 1


# --- Metric rendering ---------------------------------------------------------

def _render_instances() -> list[str]:
    """Return exposition lines for the per-provider instance gauge."""
    # Imported lazily to avoid pulling the whole dashboard import graph when a
    # provider is imported in isolation (e.g. unit tests).
    from state_reader import get_instances

    try:
        instances = get_instances()
    except Exception:  # noqa: BLE001 - never fail the /metrics scrape
        instances = []

    by_provider: "collections.Counter[str]" = collections.Counter(
        (i.provider for i in instances)
    )

    lines = [
        "# HELP skydash_instances Number of managed instances per cloud provider.",
        "# TYPE skydash_instances gauge",
    ]
    for provider, count in sorted(by_provider.items()):
        if not provider:
            continue
        # Provider keys are safe label values (lower-case alpha, validated by models).
        lines.append(f'skydash_instances{{provider="{provider}"}} {count}')
    return lines


def render_metrics() -> str:
    """Render the full /metrics payload in Prometheus text exposition format."""
    uptime = int(time.time() - _process_start)
    with _requests_lock:
        requests = _requests_total

    lines: list[str] = [
        "# HELP skydash_up Whether the SkyDash API is up (1 = up, 0 = down).",
        "# TYPE skydash_up gauge",
        "skydash_up 1",
        "# HELP skydash_uptime_seconds Seconds since the SkyDash process started.",
        "# TYPE skydash_uptime_seconds counter",
        f"skydash_uptime_seconds {uptime}",
    ]
    lines += _render_instances()
    lines += [
        "# HELP skydash_http_requests_total Total HTTP requests handled by SkyDash.",
        "# TYPE skydash_http_requests_total counter",
        f"skydash_http_requests_total {requests}",
    ]
    # A trailing newline is required for strict text-format parsers.
    return "\n".join(lines) + "\n"
