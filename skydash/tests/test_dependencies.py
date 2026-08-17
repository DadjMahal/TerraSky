"""Tests for dependencies — resource relationship graph (§88)."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dependencies


def _inst(slug, tags=None):
    return type("Inst", (), {"slug": slug, "tags": tags or {}})()


# --------------------------------------------------------------------------- #
# build_graph — happy paths                                                    #
# --------------------------------------------------------------------------- #
def test_build_graph_single_node():
    graph = dependencies.build_graph([_inst("web-1")])
    assert graph == {"web-1": {"dependencies": [], "dependents": [], "app": None}}


def test_build_graph_explicit_dependency():
    graph = dependencies.build_graph([
        _inst("web-1", {"depends_on": "db-1, cache-1"}),
        _inst("db-1"),
        _inst("cache-1"),
    ])
    assert sorted(graph["web-1"]["dependencies"]) == ["cache-1", "db-1"]
    assert "web-1" in graph["db-1"]["dependents"]
    assert "web-1" in graph["cache-1"]["dependents"]


def test_build_graph_dependency_key_is_alias():
    graph = dependencies.build_graph([
        _inst("web-1", {"dependency": "db-1"}),
        _inst("db-1"),
    ])
    assert graph["web-1"]["dependencies"] == ["db-1"]


def test_build_graph_no_self_dependency():
    graph = dependencies.build_graph([
        _inst("web-1", {"depends_on": "web-1"}),
    ])
    assert graph["web-1"]["dependencies"] == []
    assert graph["web-1"]["dependents"] == []


def test_build_graph_ignores_unknown_slug():
    graph = dependencies.build_graph([
        _inst("web-1", {"depends_on": "missing"}),
    ])
    assert graph["web-1"]["dependencies"] == []


def test_build_graph_dedupes_duplicate_dependencies():
    graph = dependencies.build_graph([
        _inst("web-1", {"depends_on": "db-1, db-1"}),
        _inst("db-1"),
    ])
    assert graph["web-1"]["dependencies"] == ["db-1"]
    assert graph["db-1"]["dependents"] == ["web-1"]


def test_build_graph_app_tag_recorded():
    graph = dependencies.build_graph([_inst("web-1", {"app": "shop"})])
    assert graph["web-1"]["app"] == "shop"


def test_build_graph_cluster_for_shared_app():
    graph = dependencies.build_graph([
        _inst("web-1", {"app": "shop"}),
        _inst("web-2", {"app": "shop"}),
        _inst("db-1", {"app": "shop"}),
        _inst("other", {"app": "other"}),
    ])
    assert graph["web-1"]["cluster"] == "app:web-1"
    assert graph["web-2"]["cluster"] == "app:web-1"
    assert graph["db-1"]["cluster"] == "app:web-1"
    assert "cluster" not in graph["other"]


# --------------------------------------------------------------------------- #
# Edge cases                                                                   #
# --------------------------------------------------------------------------- #
def test_build_graph_handles_missing_tags():
    inst = type("Inst", (), {"slug": "web-1"})()
    graph = dependencies.build_graph([inst])
    assert graph["web-1"]["dependencies"] == []


def test_build_graph_handles_non_string_tag_values():
    graph = dependencies.build_graph([
        type("Inst", (), {"slug": "web-1", "tags": {"app": 123, "depends_on": None}})(),
    ])
    assert graph["web-1"]["app"] == "123"


def test_build_graph_no_cluster_for_single_member():
    graph = dependencies.build_graph([_inst("web-1", {"app": "solo"})])
    assert "cluster" not in graph["web-1"]


def test_norm_app_lowercases_and_hyphenates():
    assert dependencies._norm_app("My Shop") == "my-shop"


def test_dependencies_and_dependents_empty_for_unknown_slug():
    assert dependencies.dependencies({}, "missing") == []
    assert dependencies.dependents({}, "missing") == []


def test_dependencies_and_dependents_helpers():
    graph = dependencies.build_graph([
        _inst("web-1", {"depends_on": "db-1"}),
        _inst("db-1"),
    ])
    assert dependencies.dependencies(graph, "web-1") == ["db-1"]
    assert dependencies.dependents(graph, "db-1") == ["web-1"]


# --------------------------------------------------------------------------- #
# as_topology                                                                  #
# --------------------------------------------------------------------------- #
def test_as_topology_nodes_and_edges():
    graph = dependencies.build_graph([
        _inst("web-1", {"depends_on": "db-1", "app": "shop"}),
        _inst("db-1", {"app": "shop"}),
    ])
    topo = dependencies.as_topology(graph)
    assert len(topo["nodes"]) == 2
    node_ids = {n["id"] for n in topo["nodes"]}
    assert node_ids == {"web-1", "db-1"}
    assert {"source": "web-1", "target": "db-1"} in topo["edges"]


def test_as_topology_no_edges_when_none():
    topo = dependencies.as_topology({"web-1": {"dependencies": [], "dependents": [], "app": None}})
    assert topo["edges"] == []


if __name__ == "__main__":
    import pytest as _pytest
    sys.exit(_pytest.main([__file__, "-v"]))
