"""Tests for drift — desired/live state comparison and drift sweep (§15).

Pure stdlib. The provider registry is patched out so no cloud SDKs/credentials
are needed; real provider objects are never constructed.
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import drift


# --------------------------------------------------------------------------- #
# compare — single desired/live status comparison                             #
# --------------------------------------------------------------------------- #
def test_compare_in_sync():
    result = drift.compare("running", "running")
    assert result["drifted"] is False
    assert result["live_state"] == "running"
    assert result["note"] == "in sync"


def test_compare_drifted_running_vs_stopped():
    result = drift.compare("running", "stopped")
    assert result["drifted"] is True
    assert result["live_state"] == "stopped"
    assert result["note"] == "desired/live state class mismatch"


def test_compare_class_matching_aliases_in_sync():
    """active maps to the running class, so no false drift."""
    result = drift.compare("running", "active")
    assert result["drifted"] is False
    assert result["live_state"] == "active"


def test_compare_whitespace_and_case_normalized():
    result = drift.compare("RUNNING", "  stopped ")
    assert result["drifted"] is True
    assert result["live_state"] == "stopped"


def test_compare_desired_other_class_drifts():
    result = drift.compare("starting", "running")
    assert result["drifted"] is True


def test_compare_unverifiable_unknown_live():
    result = drift.compare("running", "unknown")
    assert result["drifted"] is False
    assert result["live_state"] == "unknown"
    assert "unverifiable" in result["note"]


def test_compare_unverifiable_error_live():
    result = drift.compare("running", "error")
    assert result["drifted"] is False
    assert "unverifiable" in result["note"]


def test_compare_unverifiable_empty_live_defaults_to_unknown():
    result = drift.compare("running", "")
    assert result["drifted"] is False
    assert result["live_state"] == "unknown"
    assert "unverifiable" in result["note"]


# --------------------------------------------------------------------------- #
# detect_instances — sweep over the desired inventory                         #
# --------------------------------------------------------------------------- #
def _make_inst(*, provider, slug="s", name="n", status="running"):
    return SimpleNamespace(provider=provider, slug=slug, name=name, status=status)


def test_detect_instances_provider_unavailable_marked_unverifiable():
    provider = mock.Mock()
    provider.available.return_value = False
    with mock.patch.object(drift, "get_provider", return_value=provider):
        results = drift.detect_instances([_make_inst(provider="aws", slug="web-1")])
    assert len(results) == 1
    row = results[0]
    assert row["slug"] == "web-1"
    assert row["drifted"] is False
    assert row["live"] == "unverifiable"
    assert "unavailable" in row["note"]


def test_detect_instances_unknown_provider_marked_unverifiable():
    with mock.patch.object(drift, "get_provider", return_value=None):
        results = drift.detect_instances([_make_inst(provider="nope")])
    assert results[0]["live"] == "unverifiable"
    assert results[0]["drifted"] is False


def test_detect_instances_in_sync_live_fetch():
    provider = mock.Mock()
    provider.available.return_value = True
    provider.get_status.return_value = ("running", None, None, None)
    inst = _make_inst(provider="aws", slug="web-1", name="Web", status="running")
    with mock.patch.object(drift, "get_provider", return_value=provider):
        results = drift.detect_instances([inst])
    row = results[0]
    assert row["drifted"] is False
    assert row["live"] == "running"
    assert row["desired"] == "running"


def test_detect_instances_drifted_live_fetch():
    provider = mock.Mock()
    provider.available.return_value = True
    provider.get_status.return_value = ("stopped", None, None, None)
    inst = _make_inst(provider="aws", slug="web-1", status="running")
    with mock.patch.object(drift, "get_provider", return_value=provider):
        results = drift.detect_instances([inst])
    assert results[0]["drifted"] is True
    assert results[0]["live"] == "stopped"


def test_detect_instances_uses_error_over_note():
    provider = mock.Mock()
    provider.available.return_value = True
    provider.get_status.return_value = ("stopped", "fetch failed", None, None)
    inst = _make_inst(provider="aws", status="running")
    with mock.patch.object(drift, "get_provider", return_value=provider):
        results = drift.detect_instances([inst])
    assert results[0]["note"] == "fetch failed"


def test_detect_instances_exception_does_not_abort_sweep():
    provider = mock.Mock()
    provider.available.return_value = True
    provider.get_status.side_effect = RuntimeError("boom")
    inst = _make_inst(provider="aws", slug="web-1")
    with mock.patch.object(drift, "get_provider", return_value=provider):
        results = drift.detect_instances([inst])
    assert len(results) == 1
    assert results[0]["live"] == "unverifiable"
    assert "boom" in results[0]["note"]


def test_detect_instances_empty_input():
    assert drift.detect_instances([]) == []


# --------------------------------------------------------------------------- #
# summarize                                                                   #
# --------------------------------------------------------------------------- #
def test_summarize_counts_categories():
    results = [
        {"drifted": True, "live": "stopped", "note": "mismatch"},
        {"drifted": False, "live": "running", "note": "in sync"},
        {"drifted": False, "live": "unverifiable", "note": "unverifiable: x"},
        {"drifted": False, "live": "running", "note": "unverifiable: y"},
    ]
    counts = drift.summarize(results)
    assert counts == {"in_sync": 1, "drifted": 1, "unverifiable": 2, "total": 4}


def test_summarize_empty():
    counts = drift.summarize([])
    assert counts == {"in_sync": 0, "drifted": 0, "unverifiable": 0, "total": 0}


def test_summarize_treats_unverifiable_note_as_unverifiable():
    counts = drift.summarize([{"drifted": False, "live": "running",
                               "note": "unverifiable: provider unavailable"}])
    assert counts["unverifiable"] == 1
    assert counts["in_sync"] == 0

