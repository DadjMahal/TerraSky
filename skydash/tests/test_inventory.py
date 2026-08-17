"""Tests for inventory — global inventory indexing, search and summarize (§57, §59).

Pure stdlib; instances are represented as simple namespace objects so no cloud
SDKs are required.
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import inventory


def _inst(**kwargs):
    base = dict(slug="web-1", name="Web Server", provider="aws", region="us-east-1",
                instance_type="t3.micro", status="running",
                tags={"env": "prod", "Name": "web-1"})
    base.update(kwargs)
    return SimpleNamespace(**base)


# --------------------------------------------------------------------------- #
# build_index                                                                 #
# --------------------------------------------------------------------------- #
def test_build_index_rows_exclude_underscore_fields():
    index = inventory.build_index([_inst()])
    assert len(index) == 1
    row = index[0]
    assert row["slug"] == "web-1"
    assert row["provider"] == "aws"
    assert row["status"] == "running"
    # _haystack present but non-underscore keys only
    assert "_haystack" in row


def test_build_index_haystack_lowercases_all_fields():
    index = inventory.build_index([_inst(name="Web Server", region="US-East-1")])
    hay = index[0]["_haystack"]
    assert "web server" in hay
    assert "us-east-1" in hay
    assert "running" in hay
    assert "env:prod" in hay  # tag rendered as key:value


def test_build_index_empty():
    assert inventory.build_index([]) == []


def test_build_index_missing_attributes_defaults():
    inst = SimpleNamespace(slug="bare")
    index = inventory.build_index([inst])
    row = index[0]
    assert row["name"] == ""
    assert row["provider"] == ""
    assert row["region"] == ""
    assert row["tags"] == {}


# --------------------------------------------------------------------------- #
# search                                                                      #
# --------------------------------------------------------------------------- #
def _index():
    return inventory.build_index([
        _inst(slug="web-1", name="Web Server", provider="aws", status="running"),
        _inst(slug="db-1", name="Postgres DB", provider="aws", status="stopped"),
        _inst(slug="calc-1", name="Compute", provider="azure", status="running"),
    ])


def test_search_empty_query_returns_all_excluding_underscores():
    rows = inventory.search(_index())
    assert len(rows) == 3
    assert all("_haystack" not in r for r in rows)


def test_search_substring_case_insensitive():
    rows = inventory.search(_index(), query="postgres")
    assert len(rows) == 1
    assert rows[0]["slug"] == "db-1"


def test_search_matches_provider_field():
    rows = inventory.search(_index(), query="azure")
    assert len(rows) == 1
    assert rows[0]["slug"] == "calc-1"


def test_search_no_match_returns_empty():
    assert inventory.search(_index(), query="nomatch") == []


def test_search_provider_filter():
    rows = inventory.search(_index(), provider="aws")
    assert {r["slug"] for r in rows} == {"web-1", "db-1"}


def test_search_status_filter_case_insensitive():
    rows = inventory.search(_index(), status="RUNNING")
    assert {r["slug"] for r in rows} == {"web-1", "calc-1"}


def test_search_combined_query_and_filters():
    rows = inventory.search(_index(), query="web", provider="aws", status="running")
    assert [r["slug"] for r in rows] == ["web-1"]


def test_search_empty_index():
    assert inventory.search([], query="x") == []


# --------------------------------------------------------------------------- #
# summarize                                                                   #
# --------------------------------------------------------------------------- #
def test_summarize_counts_by_provider_and_status():
    summary = inventory.summarize(_index())
    assert summary["total"] == 3
    assert summary["by_provider"] == {"aws": 2, "azure": 1}
    assert summary["by_status"] == {"running": 2, "stopped": 1}


def test_summarize_empty_index():
    assert inventory.summarize([]) == {"total": 0, "by_provider": {}, "by_status": {}}
