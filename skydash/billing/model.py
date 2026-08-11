"""Financial core entities (§51-56): CostRecord, Invoice, allocation math.

Pure data + math so the pipeline is unit-testable without any provider keys.
Currency conversion uses a small documented static table (rates as of 2026-08);
real FX rates are a later external integration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

# Static FX reference (USD base, 2026-08 snapshot). Replace with live FX API.
USD_RATES: dict[str, Decimal] = {
    "USD": Decimal("1.0"), "EUR": Decimal("1.08"), "GBP": Decimal("1.27"),
    "INR": Decimal("0.012"), "JPY": Decimal("0.0068"), "CNY": Decimal("0.14"),
}


def to_usd(amount: Decimal, currency: str) -> Decimal:
    """Normalize an amount to USD for cross-provider total comparisons (§53)."""
    rate = USD_RATES.get((currency or "USD").upper(), Decimal("1"))
    return (Decimal(str(amount)) * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class CostRecord:
    provider: str
    resource_slug: str
    service: str = ""
    region: str = ""
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    period_start: str = ""
    period_end: str = ""
    project: str | None = None
    allocation: str = "exact"  # exact | estimated (§52)

    def to_dict(self) -> dict:
        return {**self.__dict__, "amount": str(self.amount)}


@dataclass
class Invoice:
    provider: str
    invoice_number: str
    period_start: str = ""
    period_end: str = ""
    currency: str = "USD"
    amount: Decimal = Decimal("0")
    status: str = "open"  # open|paid|overdue|void|unknown


def total_by_provider(records: list[CostRecord]) -> dict[str, str]:
    totals: dict[str, Decimal] = {}
    for r in records:
        totals[r.provider] = totals.get(r.provider, Decimal("0")) + to_usd(r.amount, r.currency)
    return {k: str(v) for k, v in sorted(totals.items())}


def total_by_project(records: list[CostRecord]) -> dict[str, str]:
    totals: dict[str, Decimal] = {}
    for r in records:
        p = r.project or "unallocated"
        totals[p] = totals.get(p, Decimal("0")) + to_usd(r.amount, r.currency)
    return {k: str(v) for k, v in sorted(totals.items())}


def rollup_by_period(records: list[CostRecord]) -> dict[str, str]:
    """Group costs by (period_start) for time-series charts (§54)."""
    totals: dict[str, Decimal] = {}
    for r in records:
        key = r.period_start or "unknown"
        totals[key] = totals.get(key, Decimal("0")) + to_usd(r.amount, r.currency)
    return {k: str(v) for k, v in sorted(totals.items())}


def validate_record(r: dict) -> list[str]:
    """Return a list of validation problems for a raw import row (§56)."""
    problems = []
    if not r.get("provider"):
        problems.append("provider required")
    if not r.get("resource_slug"):
        problems.append("resource_slug required")
    try:
        Decimal(str(r.get("amount")))
    except Exception:  # noqa: BLE001
        problems.append("amount must be numeric")
    if not r.get("period_start") or not r.get("period_end"):
        problems.append("period_start/period_end required")
    return problems
