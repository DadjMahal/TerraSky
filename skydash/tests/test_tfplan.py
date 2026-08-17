"""Tests for tfplan — pure-stdlib Terraform plan parser (§102-104).

No Terraform binary is invoked; all parsing is done on in-memory dicts or
small fixture files written to a tmp dir.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tfplan


def _full_plan():
    return {
        "format_version": "1.2",
        "terraform_version": "1.8.5",
        "resource_changes": [
            {"address": "aws_instance.web", "type": "aws_instance", "name": "web",
             "change": {"actions": ["create"], "before": None, "after": {"id": "i-1"}}},
            {"address": "aws_instance.db", "type": "aws_instance", "name": "db",
             "change": {"actions": ["update"], "before": {"x": 1}, "after": {"x": 2}}},
            {"address": "aws_sg.old", "type": "aws_security_group", "name": "old",
             "change": {"actions": ["delete"], "before": {"id": "sg-1"}, "after": None}},
            {"address": "aws_instance.stable", "type": "aws_instance", "name": "stable",
             "change": {"actions": ["no-op"], "before": {}, "after": {}}},
        ],
    }


# --------------------------------------------------------------------------- #
# parse_plan — dict input                                                     #
# --------------------------------------------------------------------------- #
def test_parse_plan_happy_path_counts_all_actions():
    result = tfplan.parse_plan(_full_plan())
    assert result["available"] is True
    assert result["format_version"] == "1.2"
    assert result["terraform_version"] == "1.8.5"
    assert result["summary"] == {
        "create": 1, "update": 1, "delete": 1, "noop": 1, "total": 4,
    }


def test_parse_plan_resource_change_fields():
    result = tfplan.parse_plan(_full_plan())
    changes = result["resource_changes"]
    create = [c for c in changes if c["action"] == "create"][0]
    assert create["address"] == "aws_instance.web"
    assert create["type"] == "aws_instance"
    assert create["name"] == "web"
    assert create["after"] == {"id": "i-1"}


def test_parse_plan_empty_resource_changes():
    result = tfplan.parse_plan({"resource_changes": []})
    assert result["available"] is True
    assert result["summary"] == {"create": 0, "update": 0, "delete": 0,
                                 "noop": 0, "total": 0}
    assert result["resource_changes"] == []


def test_parse_plan_empty_dict():
    result = tfplan.parse_plan({})
    assert result["available"] is True
    assert result["summary"]["total"] == 0


def test_parse_plan_missing_change_key_is_noop():
    result = tfplan.parse_plan({"resource_changes": [{"address": "x", "type": "t",
                                                       "name": "n"}]})
    assert result["resource_changes"][0]["action"] == "noop"
    assert result["summary"]["noop"] == 1


def test_parse_plan_action_priority_create_over_update():
    plan = {"resource_changes": [{"change": {"actions": ["create", "update"]}}]}
    result = tfplan.parse_plan(plan)
    assert result["resource_changes"][0]["action"] == "create"


def test_parse_plan_action_priority_delete_over_update():
    plan = {"resource_changes": [{"change": {"actions": ["delete", "update"]}}]}
    result = tfplan.parse_plan(plan)
    assert result["resource_changes"][0]["action"] == "delete"


def test_parse_plan_empty_actions_is_noop():
    plan = {"resource_changes": [{"change": {"actions": []}}]}
    result = tfplan.parse_plan(plan)
    assert result["resource_changes"][0]["action"] == "noop"


def test_parse_plan_unknown_action_passthrough():
    plan = {"resource_changes": [{"change": {"actions": ["read"]}}]}
    result = tfplan.parse_plan(plan)
    assert result["resource_changes"][0]["action"] == "read"
    assert result["summary"].get("read") == 1


def test_parse_plan_not_a_dict():
    result = tfplan.parse_plan([1, 2, 3])
    assert result["available"] is False
    assert result["error"] == "plan is not a JSON object"


def test_parse_plan_none_input():
    result = tfplan.parse_plan(None)
    assert result["available"] is False
    assert "not a JSON object" in result["error"]


# --------------------------------------------------------------------------- #
# parse_plan — file path input                                                #
# --------------------------------------------------------------------------- #
def test_parse_plan_from_file(tmp_path):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(_full_plan()))
    result = tfplan.parse_plan(str(path))
    assert result["available"] is True
    assert result["summary"]["total"] == 4


def test_parse_plan_from_pathlib_path(tmp_path):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(_full_plan()))
    result = tfplan.parse_plan(Path(path))
    assert result["available"] is True


def test_parse_plan_file_nonexistent(tmp_path):
    result = tfplan.parse_plan(str(tmp_path / "missing.json"))
    assert result["available"] is False
    assert "failed to read plan" in result["error"]


def test_parse_plan_file_bad_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json")
    result = tfplan.parse_plan(str(path))
    assert result["available"] is False
    assert "failed to read plan" in result["error"]


def test_parse_plan_file_top_level_list(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[1, 2]")
    result = tfplan.parse_plan(str(path))
    assert result["available"] is False
    assert "not a JSON object" in result["error"]


# --------------------------------------------------------------------------- #
# parse_plan_file convenience wrapper                                         #
# --------------------------------------------------------------------------- #
def test_parse_plan_file_wrapper(tmp_path):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(_full_plan()))
    result = tfplan.parse_plan_file(str(path))
    assert result["available"] is True
    assert result["summary"]["create"] == 1

