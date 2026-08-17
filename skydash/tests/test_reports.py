"""Tests for reports — CSV/JSON report builders over inventory + cost records
(§92-93).

The module functions are pure (no I/O), so the exact bytes of the CSV output
are unit-testable. We drive DictWriter/JSON building through mocks to verify
the writers are invoked as expected, without touching any real filesystem.
"""
from __future__ import annotations

import csv
import io
import os
import sys
from decimal import Decimal
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import reports  # noqa: E402
from billing.model import CostRecord  # noqa: E402

INVENTORY = [
    {
        "slug": "web-1",
        "name": "Primary Web",
        "provider": "aws",
        "region": "us-east-1",
        "instance_type": "t3.micro",
        "status": "running",
    },
    {
        "slug": "db-1",
        "name": "Primary DB",
        "provider": "gcp",
        "region": "us-central1",
        "instance_type": "n2-standard-2",
        "status": "stopped",
    },
]

COSTS = [
    CostRecord(
        provider="aws",
        resource_slug="web-1",
        service="ec2",
        region="us-east-1",
        amount=Decimal("12.50"),
        currency="USD",
        project="platform",
    ),
    CostRecord(
        provider="gcp",
        resource_slug="db-1",
        service="compute",
        region="us-central1",
        amount=Decimal("8.00"),
        currency="USD",
        project=None,
    ),
]

# --------------------------------------------------------------------------- #
# inventory_csv                                                               #
# --------------------------------------------------------------------------- #
def test_inventory_csv_has_header():
    text = reports.inventory_csv([])
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == ["slug", "name", "provider", "region", "instance_type", "status"]


def test_inventory_csv_empty_index_only_header():
    text = reports.inventory_csv([])
    assert text.strip() == "slug,name,provider,region,instance_type,status"


def test_inventory_csv_writes_all_rows():
    text = reports.inventory_csv(INVENTORY)
    rows = list(csv.reader(io.StringIO(text)))
    assert len(rows) == len(INVENTORY) + 1
    assert rows[1] == ["web-1", "Primary Web", "aws", "us-east-1", "t3.micro", "running"]
    assert rows[2] == ["db-1", "Primary DB", "gcp", "us-central1", "n2-standard-2", "stopped"]


def test_inventory_csv_row_values_match_input():
    text = reports.inventory_csv(INVENTORY)
    rows = list(csv.reader(io.StringIO(text)))[1:]
    for row, item in zip(rows, INVENTORY):
        assert row[0] == item["slug"]
        assert row[1] == item["name"]
        assert row[2] == item["provider"]
        assert row[3] == item["region"]
        assert row[4] == item["instance_type"]
        assert row[5] == item["status"]


def test_inventory_csv_uses_csv_writer(mocked_writer_module):
    """The builder drives csv.writer with the header + all rows."""
    reports.inventory_csv(INVENTORY)
    mock_writer = mocked_writer_module.writer.return_value
    calls = [c.args[0] for c in mock_writer.writerow.call_args_list]
    assert calls[0] == ["slug", "name", "provider", "region", "instance_type", "status"]
    assert len(calls) == len(INVENTORY) + 1


# --------------------------------------------------------------------------- #
# costs_csv                                                                   #
# --------------------------------------------------------------------------- #
def test_costs_csv_has_header():
    text = reports.costs_csv([])
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == [
        "provider", "resource_slug", "service", "region", "amount", "currency", "project",
    ]


def test_costs_csv_empty_records_only_header():
    text = reports.costs_csv([])
    assert text.strip() == "provider,resource_slug,service,region,amount,currency,project"


def test_costs_csv_writes_record_fields():
    text = reports.costs_csv(COSTS)
    rows = list(csv.reader(io.StringIO(text)))
    assert len(rows) == len(COSTS) + 1
    assert rows[1] == ["aws", "web-1", "ec2", "us-east-1", "12.50", "USD", "platform"]
    assert rows[2] == ["gcp", "db-1", "compute", "us-central1", "8.00", "USD", ""]


def test_costs_csv_none_project_renders_empty():
    """A None project becomes an empty project cell, not the string 'None'."""
    text = reports.costs_csv([CostRecord(provider="x", resource_slug="r")])
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[1][6] == ""


def test_costs_csv_amount_as_decimal_string():
    text = reports.costs_csv([CostRecord(provider="a", resource_slug="r", amount=Decimal("9.99"))])
    assert "9.99" in text


def test_costs_csv_uses_csv_writer(mocked_writer_module):
    reports.costs_csv(COSTS)
    mock_writer = mocked_writer_module.writer.return_value
    calls = [c.args[0] for c in mock_writer.writerow.call_args_list]
    assert calls[0] == [
        "provider", "resource_slug", "service", "region", "amount", "currency", "project",
    ]
    assert len(calls) == len(COSTS) + 1


# --------------------------------------------------------------------------- #
# inventory_json                                                              #
# --------------------------------------------------------------------------- #
def test_inventory_json_wraps_items():
    result = reports.inventory_json(INVENTORY)
    assert result["items"] == INVENTORY
    assert result["total"] == len(INVENTORY)


def test_inventory_json_empty():
    result = reports.inventory_json([])
    assert result["items"] == []
    assert result["total"] == 0


def test_inventory_json_preserves_order_and_data():
    result = reports.inventory_json(INVENTORY)
    assert result["items"][0]["slug"] == "web-1"
    assert result["items"][1]["slug"] == "db-1"
    assert result["items"][1]["provider"] == "gcp"


def test_inventory_json_dict_shapes():
    """The builder returns a plain dict that round-trips through json.dumps."""
    import json
    result = reports.inventory_json(INVENTORY)
    encoded = json.dumps(result)
    decoded = json.loads(encoded)
    assert decoded["total"] == 2
    assert decoded["items"][0]["name"] == "Primary Web"


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #
@pytest.fixture
def mocked_writer_module(monkeypatch):
    """Swap reports.csv with a mock so writerow calls are captured without I/O."""
    fake = mock.Mock()
    monkeypatch.setattr(reports, "csv", fake)
    return fake


if __name__ == "__main__":
    import pytest as _pytest
    sys.exit(_pytest.main([__file__, "-v"]))

