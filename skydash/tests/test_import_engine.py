"""Tests for import_engine — infra import (§14) + read-only import (§106).

Pure stdlib with heavy dependencies fully mocked: the source inventory
(state_reader.get_instances) and the config store are replaced with mocks so
no JSON file, Flask or cloud SDK is touched.
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import import_engine


def _inst(provider="aws", instance_id="i-1", name="web", slug="aws-web",
          region="us-east-1", instance_type="t3.micro"):
    return SimpleNamespace(provider=provider, instance_id=instance_id,
                           name=name, slug=slug, region=region,
                           instance_type=instance_type)


def test_import_inventory_empty_inventory():
    with mock.patch.object(import_engine, "get_instances", return_value=[]), \
         mock.patch.object(import_engine.config_store, "get_custom_instances",
                           return_value=[]):
        result = import_engine.import_inventory()
    assert result == {"imported": 0, "skipped": 0, "errors": 0}


def test_import_inventory_imports_new_instances_readonly():
    insts = [_inst(instance_id="i-1"), _inst(provider="aws", instance_id="i-2")]
    add = mock.Mock()
    with mock.patch.object(import_engine, "get_instances", return_value=insts), \
         mock.patch.object(import_engine.config_store, "get_custom_instances",
                           return_value=[]), \
         mock.patch.object(import_engine.config_store, "add_custom_instance", add):
        result = import_engine.import_inventory(readonly=True)
    assert result == {"imported": 2, "skipped": 0, "errors": 0}
    assert add.call_count == 2
    calls = [c.kwargs for c in add.call_args_list]
    assert calls[0]["instance_id"] == "i-1"
    assert calls[1]["instance_id"] == "i-2"
    assert all(c["readonly"] is True for c in calls)
    assert calls[0]["name"] == "web"
    assert calls[0]["region"] == "us-east-1"


def test_import_inventory_skips_existing_instance_id():
    insts = [_inst(instance_id="i-1")]
    add = mock.Mock()
    existing = [{"instance_id": "i-1", "readonly": True}]
    with mock.patch.object(import_engine, "get_instances", return_value=insts), \
         mock.patch.object(import_engine.config_store, "get_custom_instances",
                           return_value=existing), \
         mock.patch.object(import_engine.config_store, "add_custom_instance", add):
        result = import_engine.import_inventory()
    assert result == {"imported": 0, "skipped": 1, "errors": 0}
    add.assert_not_called()


def test_import_inventory_skips_instance_without_id():
    insts = [_inst(instance_id="   ")]
    with mock.patch.object(import_engine, "get_instances", return_value=insts), \
         mock.patch.object(import_engine.config_store, "get_custom_instances",
                           return_value=[]), \
         mock.patch.object(import_engine.config_store, "add_custom_instance") as add:
        result = import_engine.import_inventory()
    assert result == {"imported": 0, "skipped": 1, "errors": 0}
    add.assert_not_called()


def test_import_inventory_counts_add_errors():
    insts = [_inst(instance_id="i-1"), _inst(instance_id="i-2")]
    add = mock.Mock(side_effect=RuntimeError("store down"))
    with mock.patch.object(import_engine, "get_instances", return_value=insts), \
         mock.patch.object(import_engine.config_store, "get_custom_instances",
                           return_value=[]), \
         mock.patch.object(import_engine.config_store, "add_custom_instance", add):
        result = import_engine.import_inventory()
    assert result == {"imported": 0, "skipped": 0, "errors": 2}


def test_import_inventory_provider_filter_ignores_others():
    insts = [_inst(provider="aws", instance_id="i-1"),
             _inst(provider="azure", instance_id="i-2")]
    with mock.patch.object(import_engine, "get_instances", return_value=insts), \
         mock.patch.object(import_engine.config_store, "get_custom_instances",
                           return_value=[]), \
         mock.patch.object(import_engine.config_store, "add_custom_instance") as add:
        result = import_engine.import_inventory(provider="aws")
    assert result == {"imported": 1, "skipped": 0, "errors": 0}
    add.assert_called_once()
    assert add.call_args.kwargs["provider"] == "aws"



def test_import_inventory_filtered_out_instance_not_counted():
    """Filtered-out instances are skipped entirely (not counted as skipped)."""
    insts = [_inst(provider="azure", instance_id="i-2")]
    with mock.patch.object(import_engine, "get_instances", return_value=insts), \
         mock.patch.object(import_engine.config_store, "get_custom_instances",
                           return_value=[]), \
         mock.patch.object(import_engine.config_store, "add_custom_instance"):
        result = import_engine.import_inventory(provider="aws")
    assert result == {"imported": 0, "skipped": 0, "errors": 0}


def test_import_inventory_readonly_false_marks_writable():
    insts = [_inst(instance_id="i-1")]
    add = mock.Mock()
    with mock.patch.object(import_engine, "get_instances", return_value=insts), \
         mock.patch.object(import_engine.config_store, "get_custom_instances",
                           return_value=[]), \
         mock.patch.object(import_engine.config_store, "add_custom_instance", add):
        import_engine.import_inventory(readonly=False)
    assert add.call_args.kwargs["readonly"] is False


def test_imported_count_counts_only_readonly():
    custom = [
        {"instance_id": "a", "readonly": True},
        {"instance_id": "b", "readonly": False},
        {"instance_id": "c", "readonly": True},
    ]
    with mock.patch.object(import_engine.config_store, "get_custom_instances",
                           return_value=custom):
        assert import_engine.imported_count() == 2


def test_imported_count_empty():
    with mock.patch.object(import_engine.config_store, "get_custom_instances",
                           return_value=[]):
        assert import_engine.imported_count() == 0
