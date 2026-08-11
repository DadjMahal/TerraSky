"""Budgets (§55) — spend vs threshold evaluation. Advisory: budgets NEVER
auto-shutdown resources by default (documented, §142 non-goals)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from billing.model import to_usd

THRESHOLD_WARN = Decimal("0.70")
THRESHOLD_CRITICAL = Decimal("0.90")


def evaluate(records, budget_amount: Decimal, currency: str = "USD",
             project: str | None = None) -> dict[str, Any]:
    """Return spend status vs a monthly budget.

    ``records``: iterable of CostRecord (already filtered to the project if given).
    """
    spent = sum((to_usd(r.amount, r.currency) for r in records), Decimal("0"))
    budget = Decimal(str(budget_amount))
    pct = (spent / budget) if budget else Decimal("0")
    pct = min(pct, Decimal("9.99"))
    if pct >= Decimal("1.0"):
        level, action = "exceeded", "incident"
    elif pct >= THRESHOLD_CRITICAL:
        level, action = "critical", "notify + incident"
    elif pct >= THRESHOLD_WARN:
        level, action = "warn", "notify"
    else:
        level, action = "ok", "none"
    return {"spent": str(spent), "budget": str(budget), "percent": str(int(round(pct * 100))),
            "level": level, "action": action, "currency": currency,
            "thresholds": {"warn": str(THRESHOLD_WARN), "critical": str(THRESHOLD_CRITICAL)}}
