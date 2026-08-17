"""Tests for health — threshold-based alert evaluation (§44-46)."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import health


def _inst(slug="web-1", name="Web 1", status="ok", provider="aws"):
    return type("Inst", (), {"slug": slug, "name": name, "status": status,
                             "provider": provider})()


# --------------------------------------------------------------------------- #
# evaluate_row — happy paths                                                   #
# --------------------------------------------------------------------------- #
def test_evaluate_row_no_hits_on_ok_status():
    assert health.evaluate_row("ok") == []


def test_evaluate_row_error_status_is_critical():
    hits = health.evaluate_row("error")
    assert any(h["id"] == "AL-001" and h["severity"] == "critical" for h in hits)


def test_evaluate_row_disk_threshold_triggered():
    hits = health.evaluate_row("ok", {"disk_pct": 95})
    assert any(h["id"] == "AL-002" and h["severity"] == "warning" for h in hits)


def test_evaluate_row_disk_below_threshold():
    hits = health.evaluate_row("ok", {"disk_pct": 50})
    assert not any(h["id"] == "AL-002" for h in hits)


def test_evaluate_row_cpu_threshold_boundary():
    hits = health.evaluate_row("ok", {"cpu_pct": 95})
    assert any(h["id"] == "AL-003" for h in hits)
    hits = health.evaluate_row("ok", {"cpu_pct": 94.9})
    assert not any(h["id"] == "AL-003" for h in hits)


def test_evaluate_row_percent_string_value():
    hits = health.evaluate_row("ok", {"disk_pct": "91%"})
    assert any(h["id"] == "AL-002" for h in hits)


def test_evaluate_row_eq_matches_case_insensitively():
    hits = health.evaluate_row("ERROR")
    assert any(h["id"] == "AL-001" for h in hits)


# --------------------------------------------------------------------------- #
# evaluate_row — edge cases                                                    #
# --------------------------------------------------------------------------- #
def test_evaluate_row_custom_rules():
    rules = [{"id": "T1", "match": "*", "field": "load", "gte": 4,
              "severity": "info", "message": "high load"}]
    hits = health.evaluate_row("ok", {"load": 5}, rules=rules)
    assert len(hits) == 1
    assert hits[0]["id"] == "T1"


def test_evaluate_row_missing_field_skipped():
    hits = health.evaluate_row("ok", {"disk_pct": None})
    assert not any(h["id"] == "AL-002" for h in hits)


def test_num_invalid_value_returns_inf():
    assert health._num("nope") == float("inf")


def test_num_strips_percent():
    assert health._num("90.5%") == 90.5


# --------------------------------------------------------------------------- #
# evaluate_fleet                                                               #
# --------------------------------------------------------------------------- #
def test_evaluate_fleet_aggregates_with_instance_metadata():
    instances = [
        _inst(slug="web-1", name="Web 1", status="error", provider="aws"),
        _inst(slug="db-1", name="DB 1", status="ok", provider="gcp"),
    ]
    extra_by_slug = {"db-1": {"disk_pct": 97}}
    alerts = health.evaluate_fleet(instances, extra_by_slug)
    assert len(alerts) == 2
    web = [a for a in alerts if a["slug"] == "web-1"][0]
    assert web["name"] == "Web 1"
    assert web["provider"] == "aws"
    db = [a for a in alerts if a["slug"] == "db-1"][0]
    assert db["id"] == "AL-002"


def test_evaluate_fleet_no_extra():
    instances = [_inst(status="ok")]
    assert health.evaluate_fleet(instances) == []


def test_evaluate_fleet_handles_missing_attributes():
    inst = type("Inst", (), {})()
    alerts = health.evaluate_fleet([inst])
    assert alerts == []


if __name__ == "__main__":
    import pytest as _pytest
    sys.exit(_pytest.main([__file__, "-v"]))
