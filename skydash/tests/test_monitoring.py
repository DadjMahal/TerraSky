"""Runtime tests for Iteration 7 monitoring & financials modules. No Flask needed."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _inst(slug, provider="aws", region="us-east-1", status="running", itype="t3.micro", tags=None):
    class _I:
        pass
    i = _I()
    i.slug, i.name, i.provider, i.region = slug, slug, provider, region
    i.status, i.instance_type = status, itype
    i.tags = tags or {}
    return i


def test_inventory_search_and_filters():
    import inventory

    idx = inventory.build_index([
        _inst("aws-hermes", provider="aws", tags={"app": "hermes"}),
        _inst("oci-db", provider="oracle", status="stopped"),
        _inst("do-web", provider="digitalocean"),
    ])
    assert inventory.search(idx, query="hermes")[0]["slug"] == "aws-hermes"
    assert inventory.search(idx, query="db")[0]["slug"] == "oci-db"
    assert inventory.search(idx, provider="oracle")[0]["slug"] == "oci-db"
    assert inventory.search(idx, status="stopped")[0]["slug"] == "oci-db"
    assert inventory.search(idx, query="missing") == []
    assert inventory.summarize(idx)["total"] == 3


def test_health_alerts_thresholds():
    import health

    disk = health.evaluate_row("running", {"disk_pct": 95})
    assert any(a["id"] == "AL-002" for a in disk)
    crit = health.evaluate_row("error", {})
    assert any(a["id"] == "AL-001" for a in crit)


def test_budget_evaluation():
    from billing import budgets
    from billing.model import CostRecord
    from decimal import Decimal

    recs = [CostRecord(provider="aws", resource_slug="x", amount=Decimal("85"), currency="USD")]
    assert budgets.evaluate(recs, Decimal("100"))["level"] == "warn"            # 85% of 100
    assert budgets.evaluate(recs, Decimal("91"))["level"] == "critical"         # ~93% -> critical
    assert budgets.evaluate(recs, Decimal("75"))["level"] == "exceeded"         # >100% -> exceeded
    assert budgets.evaluate(recs, Decimal("200"))["level"] == "ok"              # 42.5% -> ok


def test_cost_rollups_and_reports():
    from billing.model import CostRecord, rollup_by_period, total_by_provider, to_usd
    from reports import costs_csv, inventory_csv

    recs = [CostRecord(provider="aws", resource_slug="a", amount=10, period_start="2026-08"),
            CostRecord(provider="oracle", resource_slug="b", amount=5, period_start="2026-08")]
    assert total_by_provider(recs)["aws"] == "10.00"
    assert rollup_by_period(recs)["2026-08"] == "15.00"
    csv_out = costs_csv(recs)
    assert csv_out.startswith("provider,resource_slug") and "aws,a" in csv_out
    assert inventory_csv([{"slug": "s", "name": "n", "provider": "p", "region": "r", "instance_type": "t", "status": "run"}]).startswith("slug,name")


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
