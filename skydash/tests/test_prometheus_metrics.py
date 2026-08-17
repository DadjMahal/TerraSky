"""Tests for prometheus_metrics — /metrics text-format exposition (§45, §82).

The module is dependency-free (stdlib only); instance data comes from
``state_reader.get_instances`` which is patched here so no real TF state is read.
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import prometheus_metrics as pm


@pytest.fixture(autouse=True)
def _reset_counter():
    pm._requests_total = 0
    yield
    pm._requests_total = 0


# --------------------------------------------------------------------------- #
# count_request                                                                #
# --------------------------------------------------------------------------- #
def test_count_request_increments_counter():
    pm.count_request()
    pm.count_request()
    pm.count_request()
    with pm._requests_lock:
        assert pm._requests_total == 3


# --------------------------------------------------------------------------- #
# _render_instances                                                            #
# --------------------------------------------------------------------------- #
def _instance(provider):
    return SimpleNamespace(provider=provider)


def test_render_instances_groups_by_provider(monkeypatch):
    monkeypatch.setattr(
        "state_reader.get_instances",
        lambda: [
            _instance("aws"),
            _instance("aws"),
            _instance("gcp"),
            _instance("aws"),
            _instance("azure"),
        ],
    )
    lines = pm._render_instances()
    text = "\n".join(lines)
    assert "# HELP skydash_instances" in text
    assert '# TYPE skydash_instances gauge' in text
    assert 'skydash_instances{provider="aws"} 3' in text
    assert 'skydash_instances{provider="gcp"} 1' in text
    assert 'skydash_instances{provider="azure"} 1' in text


def test_render_instances_skips_empty_provider(monkeypatch):
    monkeypatch.setattr(
        "state_reader.get_instances",
        lambda: [_instance(""), _instance("aws")],
    )
    lines = pm._render_instances()
    joined = "\n".join(lines)
    assert 'skydash_instances{provider=""}' not in joined
    assert 'skydash_instances{provider="aws"} 1' in joined


def test_render_instances_no_instances_emits_headers_only(monkeypatch):
    monkeypatch.setattr("state_reader.get_instances", lambda: [])
    lines = pm._render_instances()
    assert len(lines) == 2
    assert lines[0].startswith("# HELP skydash_instances")


def test_render_instances_tolerates_get_instances_error(monkeypatch):
    def boom():
        raise RuntimeError("tf state unavailable")

    monkeypatch.setattr("state_reader.get_instances", boom)
    lines = pm._render_instances()
    # Never fails the scrape: only the HELP/TYPE header lines remain.
    assert len(lines) == 2


# --------------------------------------------------------------------------- #
# render_metrics                                                               #
# --------------------------------------------------------------------------- #
def test_render_metrics_has_required_metric_families(monkeypatch):
    monkeypatch.setattr("state_reader.get_instances", lambda: [])
    out = pm.render_metrics()
    assert out.endswith("\n")
    assert "\n# HELP skydash_up" in out
    assert "\n# TYPE skydash_up gauge" in out
    assert "\nskydash_up 1\n" in out
    assert "# HELP skydash_uptime_seconds" in out
    assert "# TYPE skydash_uptime_seconds counter" in out
    assert "# HELP skydash_http_requests_total" in out
    assert "# TYPE skydash_http_requests_total counter" in out


def test_render_metrics_reports_request_count(monkeypatch):
    monkeypatch.setattr("state_reader.get_instances", lambda: [])
    pm.count_request()
    pm.count_request()
    out = pm.render_metrics()
    assert "\nskydash_http_requests_total 2\n" in out


def test_render_metrics_uptime_is_non_negative(monkeypatch):
    monkeypatch.setattr("state_reader.get_instances", lambda: [])
    out = pm.render_metrics()
    for line in out.splitlines():
        if line.startswith("skydash_uptime_seconds"):
            value = int(line.split()[-1])
            assert value >= 0
