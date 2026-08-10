"""Runtime tests for the Iteration 3 lifecycle modules (drift, dependencies,
scheduler, import engine).

Pure stdlib logic — these run WITHOUT Flask. The import-engine test is
guarded because ``config_store`` needs werkzeug (installed in production only).

Run:      python3 tests/test_lifecycle.py
    or    python3 -m pytest tests/test_lifecycle.py -v   # when pytest exists
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _mk_instance(slug: str, provider: str = "aws", status: str = "running", tags=None):
    """Lightweight stand-in holding the attributes the lifecycle modules use."""
    class _I:
        pass
    i = _I()
    i.slug = slug
    i.name = slug
    i.provider = provider
    i.status = status
    i.tags = tags or {}
    return i


# --- Drift (§15) -------------------------------------------------------------
def test_drift_compare_sync_and_drift():
    import drift

    assert drift.compare("running", "running")["drifted"] is False
    assert drift.compare("running", "stopped")["drifted"] is True
    assert drift.compare("stopped", "running")["drifted"] is True
    assert drift.compare("running", "unknown")["note"].startswith("unverifiable")
    assert drift.compare("running", "error")["drifted"] is False  # fetch error != drift


def test_drift_detect_unavailable_providers_are_honest():
    import drift

    results = drift.detect_instances([_mk_instance("x1", provider="nosuchprovider")])
    assert len(results) == 1
    assert results[0]["live"] == "unverifiable"
    assert not results[0]["drifted"]
    s = drift.summarize(results)
    assert s["unverifiable"] == 1 and s["total"] == 1


# --- Dependencies (§88) ------------------------------------------------------
def test_dependency_graph_explicit_and_app_cluster():
    import dependencies

    instances = [
        _mk_instance("web", tags={"app": "l2j", "depends_on": "db, cache"}),
        _mk_instance("db", tags={"app": "l2j"}),
        _mk_instance("cache", tags={"app": "l2j"}),
        _mk_instance("other", tags={}),
    ]
    g = dependencies.build_graph(instances)
    assert set(g["web"]["dependencies"]) == {"db", "cache"}
    assert "web" in g["db"]["dependents"]
    assert "web" in g["cache"]["dependents"]
    assert g["web"]["app"] == "l2j"
    assert dependencies.dependents(g, "db") == ["web"]
    topo = dependencies.as_topology(g)
    assert any(e == {"source": "web", "target": "db"} for e in topo["edges"])


# --- Scheduler (§91) ---------------------------------------------------------
def test_scheduler_runs_and_debounces_jobs():
    import scheduler

    sch = scheduler.Scheduler()
    calls = []
    sch.register(scheduler.Job(name="j", fn=lambda: calls.append(1), interval_seconds=60))
    assert sch.tick() == ["j"]
    assert sch.tick() == []  # debounce window still active
    assert len(calls) == 1


# --- Import engine (§14/§106) — guarded (needs werkzeug/config_store) --------
def test_import_engine_available():
    try:
        import import_engine  # noqa: F401
        from import_engine import import_inventory, imported_count  # noqa: F401
    except ImportError as exc:  # pragma: no cover - production-only deps
        import warnings

        warnings.warn(f"import_engine skipped (deployment deps missing): {exc}")
        return
    assert callable(import_inventory) and callable(imported_count)


def test_status_history_recent_events():
    import status_history as sh

    data = {
        "web": [{"ts": 100.0, "status": "running"}, {"ts": 200.0, "status": "stopped"}],
        "db": [{"ts": 150.0, "status": "running"}],
    }
    orig = sh._load
    sh._load = lambda: data
    try:
        events = sh.recent_events(["web", "db"], limit=10)
        assert events[0]["slug"] == "web" and events[0]["ts"] == 200.0, events
        assert events[-1]["slug"] == "web" and events[-1]["ts"] == 100.0, events
        assert len(sh.recent_events(["web"], limit=1)) == 1
    finally:
        sh._load = orig


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
