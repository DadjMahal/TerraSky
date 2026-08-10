# SkyDash Billing & Financial Model

> **Created:** 2026-08-10 · Source: §51-56, §92-95. Current state: NOT implemented.
> SkyDash currently shows zero cost data; this is the target design.

## 1. Billing is cost/invoice TRACKING, not payments (§51)

The platform SHALL collect + normalize financial data from providers. It MUST NOT process credit-card payments, act as a bank, or be an ERP (§142).

## 2. Core Entities

### CostRecord
```python
CostRecord:
  id: UUID
  provider: str            # aws | azure | oci | digitalocean | alibaba
  resource_id: str         # instance/droplet/vm id
  project_id: UUID | None
  environment_id: UUID | None
  service: str             # e.g. EC2, Compute
  region: str
  amount: Decimal
  currency: str            # USD, EUR
  period_start / period_end: datetime
  allocation_status: exact | estimated   # §52
  source_breakdown: dict   # raw json from provider
```

### Invoice
```python
Invoice:
  id, provider, invoice_number, period_start, period_end
  currency, amount, tax, status  # open|paid|overdue|void|unknown
  due_date, paid_date, pdf_url_or_blob
```

### UsageRecord
```python
UsageRecord:
  id, provider, resource_id, metric, quantity, unit, period, source_json
```

## 3. Billing Import Adapters (§56)

| Provider | Method | Normalize To |
|---|---|---|
| AWS | Cost Explorer API / CUR | CostRecord, Invoice, UsageRecord |
| Azure | Cost Management API | CostRecord, Invoice |
| OCI | Usage API | CostRecord |
| DigitalOcean | Billing API | CostRecord, Invoice |
| Alibaba | Billing API | CostRecord, Invoice |

Design: each adapter implements `fetch(period) -> list[CostRecord|Invoice|UsageRecord]` behind a shared `BillingAdapter` interface (mirrors the provider adapter pattern).

## 4. Budgets (§55) — default OFF for destructive actions

```
Project "l2j" monthly budget: $200
  current $143 → 71% → threshold 70% → notify
                        → 80% → notify + create incident
                        → 90% → notify + incident
                        → 100% → notify + incident (auto-shutdown DISABLED by default)
```

## 5. Cost Analytics (§54)

- Charts: cost by provider / project / resource / region / service / over time.
- Comparisons: AWS vs Azure vs OCI; this month vs last; project A vs B.

## 6. Readiness in Current App

- **Not implemented** — no billing tables, no adapters. Blocks §51-56, §92-93. No user activity required to build the adapters against public APIs; provider API keys may be the same as existing cloud credentials.