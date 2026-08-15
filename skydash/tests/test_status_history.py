"""Tests for status_history — per-slug status timeline store (#15).

Uses a temp dir via monkeypatching of _HISTORY_FILE so no real file
in the repo is touched.
"""
from __future__ import annotations

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import status_history as sh

# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _isolated_history_file(tmp_path, monkeypatch):
    """Point status_history at a temp file so tests are hermetic."""
    history_file = tmp_path / "status_history.json"
    monkeypatch.setattr(sh, "_HISTORY_FILE", str(history_file))
    yield history_file


# --------------------------------------------------------------------------- #
# record — basic append                                                        #
# --------------------------------------------------------------------------- #
def test_record_single_status():
    sh.record("web-1", "running")
    history = sh.get_history("web-1")
    assert len(history) == 1
    assert history[0]["status"] == "running"
    assert "ts" in history[0]


def test_record_preserves_order():
    sh.record("web-1", "starting")
    sh.record("web-1", "running")
    sh.record("web-1", "stopped")
    history = sh.get_history("web-1")
    assert [e["status"] for e in history] == ["starting", "running", "stopped"]


def test_record_dedupes_consecutive_same_status():
    """If the last status is the same, timestamp refreshes (no new entry)."""
    sh.record("web-1", "running")
    first = sh.get_history("web-1")[0]
    time.sleep(0.01)
    sh.record("web-1", "running")
    history = sh.get_history("web-1")
    assert len(history) == 1
    assert history[0]["status"] == "running"
    assert history[0]["ts"] >= first["ts"]


def test_record_different_statuses_not_deduped():
    sh.record("web-1", "running")
    sh.record("web-1", "stopped")
    sh.record("web-1", "running")
    history = sh.get_history("web-1")
    assert [e["status"] for e in history] == ["running", "stopped", "running"]
    assert len(history) == 3


def test_record_empty_slug_skipped():
    sh.record("", "running")
    assert sh.get_history("") == []


def test_record_empty_status_skipped():
    sh.record("web-1", "")
    assert sh.get_history("web-1") == []



# --------------------------------------------------------------------------- #
# _MAX_PER_SLUG cap                                                             #
# --------------------------------------------------------------------------- #
def test_record_respects_max_per_slug():
    for i in range(sh._MAX_PER_SLUG + 5):
        sh.record("web-1", f"status-{i}")
    history = sh.get_history("web-1")
    assert len(history) == sh._MAX_PER_SLUG
    # The last 5 entries were pruned; the most recent remain
    assert history[-1]["status"] == f"status-{sh._MAX_PER_SLUG + 4}"


# --------------------------------------------------------------------------- #
# get_history                                                                   #
# --------------------------------------------------------------------------- #
def test_get_history_unknown_slug_returns_empty():
    assert sh.get_history("does-not-exist") == []


def test_get_history_none_slug():
    assert sh.get_history(None) == []


def test_get_history_chronological():
    sh.record("db-1", "running")
    sh.record("db-1", "stopped")
    history = sh.get_history("db-1")
    ts_values = [e["ts"] for e in history]
    assert ts_values == sorted(ts_values)


def test_get_history_multiple_slugs_isolated():
    sh.record("web-1", "running")
    sh.record("db-1", "running")
    sh.record("web-1", "stopped")
    assert len(sh.get_history("web-1")) == 2
    assert len(sh.get_history("db-1")) == 1
    assert sh.get_history("web-1")[1]["status"] == "stopped"


# --------------------------------------------------------------------------- #
# recent_events                                                                 #
# --------------------------------------------------------------------------- #
def test_recent_events_newest_first():
    sh.record("web-1", "running")  # ts1
    time.sleep(0.01)
    sh.record("web-1", "stopped")  # ts2
    time.sleep(0.01)
    sh.record("db-1", "running")  # ts3
    events = sh.recent_events(["web-1", "db-1"], limit=20)
    assert len(events) == 3
    assert events[0]["slug"] == "db-1"
    assert events[1]["slug"] == "web-1"
    assert events[1]["status"] == "stopped"
    assert events[2]["slug"] == "web-1"
    assert events[2]["status"] == "running"


def test_recent_events_limit():
    sh.record("web-1", "running")
    sh.record("db-1", "running")
    sh.record("cache-1", "running")
    events = sh.recent_events(["web-1", "db-1", "cache-1"], limit=2)
    assert len(events) == 2


def test_recent_events_empty_slugs():
    events = sh.recent_events([], limit=20)
    assert events == []


def test_recent_events_unknown_slug():
    events = sh.recent_events(["unknown-slug"], limit=20)
    assert events == []


def test_recent_events_event_structure():
    sh.record("web-1", "running")
    events = sh.recent_events(["web-1"], limit=20)
    ev = events[0]
    assert set(ev.keys()) == {"slug", "ts", "status"}
    assert ev["slug"] == "web-1"
    assert ev["status"] == "running"


def test_recent_events_sorts_across_slugs():
    sh.record("a", "running")
    time.sleep(0.01)
    sh.record("b", "running")
    time.sleep(0.01)
    sh.record("c", "running")
    events = sh.recent_events(["a", "b", "c"], limit=10)
    slugs = [e["slug"] for e in events]
    assert slugs == ["c", "b", "a"]


# --------------------------------------------------------------------------- #
# _load / _save persistence                                                    #
# --------------------------------------------------------------------------- #
def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    """Directly test _save + _load persistence."""
    history_file = tmp_path / "state_test.json"
    monkeypatch.setattr(sh, "_HISTORY_FILE", str(history_file))
    data = {"web-1": [{"ts": 100.0, "status": "running"}]}
    sh._save(data)
    loaded = sh._load()
    assert loaded == data


def test_load_missing_file_returns_empty(tmp_path, monkeypatch):
    history_file = tmp_path / "nonexistent.json"
    monkeypatch.setattr(sh, "_HISTORY_FILE", str(history_file))
    assert sh._load() == {}


def test_load_corrupt_file_returns_empty(tmp_path, monkeypatch):
    history_file = tmp_path / "corrupt.json"
    monkeypatch.setattr(sh, "_HISTORY_FILE", str(history_file))
    history_file.write_text("{ this is not valid json")
    assert sh._load() == {}


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

