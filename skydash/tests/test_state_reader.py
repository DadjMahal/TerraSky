"""Tests for state_reader — Terraform state parsing onto the Instance model (§11-13).

Pure stdlib; the STATE_FILE path is redirected to a tmp dir or load_state is
mocked, so the real terraform.tfstate on disk is never read.
"""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_reader
from models import Instance


def _aws_resource():
    return {
        "mode": "managed",
        "type": "aws_instance",
        "name": "hermes",
        "instances": [{
            "attributes": {
                "id": "i-12345",
                "instance_type": "t3.micro",
                "region": "us-east-1",
                "tags": {"Name": "Hermes Web"},
                "cpu_options": [{"core_count": 2, "threads_per_core": 2}],
                "root_block_device": [{"volume_size": 8}],
            }
        }],
    }


# --------------------------------------------------------------------------- #
# load_state / helpers                                                        #
# --------------------------------------------------------------------------- #
def test_load_state_reads_state_file(tmp_path, monkeypatch):
    state_path = tmp_path / "terraform.tfstate"
    state_path.write_text(json.dumps({"version": 4, "resources": []}))
    monkeypatch.setattr(state_reader, "STATE_FILE", str(state_path))
    assert state_reader.load_state() == {"version": 4, "resources": []}


def test_first_returns_first_element():
    assert state_reader._first([10, 20]) == 10


def test_first_empty_list_returns_default():
    assert state_reader._first([], "dflt") == "dflt"


def test_first_non_list_returns_default():
    assert state_reader._first("nope", "dflt") == "dflt"


def test_s_converts_value_and_handles_none():
    assert state_reader._s(None) == ""
    assert state_reader._s(42) == "42"
    assert state_reader._s("hi") == "hi"


# --------------------------------------------------------------------------- #
# _build                                                                      #
# --------------------------------------------------------------------------- #
def test_build_returns_instance():
    inst = state_reader._build(_aws_resource())
    assert isinstance(inst, Instance)
    assert inst.slug == "aws-hermes"
    assert inst.name == "hermes"
    assert inst.provider == "aws"
    assert inst.instance_id == "i-12345"
    assert inst.region == "us-east-1"
    assert inst.display_name == "Hermes Web"


def test_build_unknown_resource_type_returns_none():
    res = {"mode": "managed", "type": "random_pet", "name": "x", "instances": [{}]}
    assert state_reader._build(res) is None


def test_build_resource_without_instances_returns_none():
    res = {"mode": "managed", "type": "aws_instance", "name": "x", "instances": []}
    assert state_reader._build(res) is None


def test_build_empty_instances_key_returns_none():
    res = {"mode": "managed", "type": "aws_instance", "name": "x"}
    assert state_reader._build(res) is None


# --------------------------------------------------------------------------- #
# Per-provider attribute mappers                                              #
# --------------------------------------------------------------------------- #
def test_map_aws_cpu_and_disk():
    attrs = {
        "cpu_options": [{"core_count": 2, "threads_per_core": 2}],
        "root_block_device": [{"volume_size": 8}],
        "tags": {"Name": "web"},
        "id": "i-1",
        "region": "us-west-2",
        "instance_type": "t3.micro",
    }
    m = state_reader._map_aws(attrs)
    assert m["cpu"] == "4 vCPU"
    assert m["disk_size"] == "8 GB"
    assert m["display_name"] == "web"
    assert m["instance_id"] == "i-1"


def test_map_aws_no_cpu_options_leaves_cpu_empty():
    m = state_reader._map_aws({"id": "i-1", "tags": {}})
    assert m["cpu"] == ""
    assert m["disk_size"] == ""


def test_map_azure_full():
    attrs = {
        "name": "vm-1", "size": "Standard_B2s", "location": "eastus",
        "zone": "1", "public_ip_address": "1.2.3.4",
        "private_ip_address": "10.0.0.5", "id": "az-1",
        "os_disk": [{"disk_size_gb": 64}],
        "source_image_reference": [{"offer": "ubuntu-22_04-lts"}],
        "resource_group_name": "rg1", "tags": {"env": "prod"},
    }
    m = state_reader._map_azure(attrs)
    assert m["os"] == "Ubuntu 22.04 LTS"
    assert m["disk_size"] == "64 GB"
    assert m["availability_zone"] == "Zone 1"
    assert m["extra"]["resource_group_name"] == "rg1"


def test_map_azure_os_unknown_offer_passthrough():
    attrs = {"source_image_reference": [{"offer": "custom-os"}]}
    m = state_reader._map_azure(attrs)
    assert m["os"] == "custom-os"


def test_map_oracle_cpu_ram_disk():
    attrs = {
        "shape": "VM.Standard2.4", "region": "us-ashburn-1",
        "availability_domain": "AD-1", "id": "ocid-1",
        "compartment_id": "ocid-comp",
        "shape_config": [{"ocpus": 2, "memory_in_gbs": 16}],
        "source_details": [{"boot_volume_size_in_gbs": 50}],
        "freeform_tags": {"env": "prod"},
    }
    m = state_reader._map_oracle(attrs)
    assert m["cpu"] == "2 vCPU"
    assert m["ram"] == "16 GB"
    assert m["disk_size"] == "50 GB"
    assert m["extra"]["compartment_id"] == "ocid-comp"


def test_map_alibaba_region_derived_from_zone():
    attrs = {"cpu": 2, "memory": 4096, "availability_zone": "cn-hangzhou-b",
             "system_disk_size": 40, "id": "ali-1",
             "security_groups": ["sg-1"]}
    m = state_reader._map_alibaba(attrs)
    assert m["cpu"] == "2 vCPU"
    assert m["ram"] == "4 GB"
    assert m["disk_size"] == "40 GB"
    # region = zone minus trailing letter; code keeps the trailing hyphen
    assert m["region"] == "cn-hangzhou-"
    assert m["security_groups"] == ["sg-1"]


def test_map_alibaba_zone_without_alpha_uses_env(monkeypatch):
    monkeypatch.setenv("ALICLOUD_REGION", "cn-shanghai")
    attrs = {"availability_zone": "cn-shanghai-9", "id": "ali-2"}
    m = state_reader._map_alibaba(attrs)
    assert m["region"] == "cn-shanghai"


def test_map_digitalocean_tags_list_to_dict():
    attrs = {"name": "droplet", "size": "s-2vcpu-2gb", "region": "nyc3",
             "ipv4_address": "1.2.3.4", "created_at": "2024-01-01",
             "tags": ["web", "prod"], "id": 123456}
    m = state_reader._map_digitalocean(attrs)
    assert m["tags"] == {"web": "web", "prod": "prod"}
    assert m["instance_id"] == "123456"
    assert m["instance_type"] == "s-2vcpu-2gb"


def test_map_digitalocean_no_id_leaves_empty():
    m = state_reader._map_digitalocean({"name": "d"})
    assert m["instance_id"] == ""



# --------------------------------------------------------------------------- #
# get_instances / get_instance_by_slug                                        #
# --------------------------------------------------------------------------- #
def test_get_instances_returns_managed_compute():
    state = {"resources": [_aws_resource()]}
    with mock.patch.object(state_reader, "load_state", return_value=state):
        instances = state_reader.get_instances()
    assert len(instances) == 1
    assert instances[0].slug == "aws-hermes"


def test_get_instances_returns_empty_when_state_unreadable():
    with mock.patch.object(state_reader, "load_state", side_effect=OSError("no file")):
        assert state_reader.get_instances() == []


def test_get_instance_by_slug_found():
    state = {"resources": [_aws_resource()]}
    with mock.patch.object(state_reader, "load_state", return_value=state):
        inst = state_reader.get_instance_by_slug("aws-hermes")
    assert inst is not None
    assert inst.slug == "aws-hermes"


def test_get_instance_by_slug_not_found():
    state = {"resources": [_aws_resource()]}
    with mock.patch.object(state_reader, "load_state", return_value=state):
        assert state_reader.get_instance_by_slug("does-not-exist") is None


# --------------------------------------------------------------------------- #
# tfstate_info                                                                #
# --------------------------------------------------------------------------- #
def test_tfstate_info_happy_path(tmp_path, monkeypatch):
    state = {
        "version": 4,
        "serial": 7,
        "lineage": "abc",
        "resources": [_aws_resource()],
    }
    state_path = tmp_path / "terraform.tfstate"
    state_path.write_text("{}")
    monkeypatch.setattr(state_reader, "STATE_FILE", str(state_path))
    with mock.patch.object(state_reader, "load_state", return_value=state), \
         mock.patch.object(state_reader, "get_instances", return_value=["i"]), \
         mock.patch.object(state_reader.os.path, "getmtime", return_value=1700000000):
        info = state_reader.tfstate_info()
    assert info["available"] is True
    assert info["terraform_version"] == 4
    assert info["serial"] == 7
    assert info["lineage"] == "abc"
    assert info["resource_count"] == 1
    assert info["managed_count"] == 1
    assert info["instance_count"] == 1
    assert info["last_modified_epoch"] == 1700000000
    assert info["workspace"] == "default"


def test_tfstate_info_unreadable_returns_unavailable():
    with mock.patch.object(state_reader, "load_state", side_effect=OSError("no")):
        info = state_reader.tfstate_info()
    assert info == {"available": False, "error": "state file not readable"}


def test_tfstate_info_mtime_error_sets_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(state_reader, "STATE_FILE", str(tmp_path / "missing"))
    with mock.patch.object(state_reader, "load_state", return_value={"resources": []}), \
         mock.patch.object(state_reader, "get_instances", return_value=[]), \
         mock.patch.object(state_reader.os.path, "getmtime", side_effect=OSError("no")):
        info = state_reader.tfstate_info()
    assert info["available"] is True
    assert info["last_modified"] == ""
    assert info["last_modified_epoch"] == 0


# --------------------------------------------------------------------------- #
# get_workspaces                                                              #
# --------------------------------------------------------------------------- #
def test_get_workspaces_from_environment_tags():
    insts = [SimpleNamespace(tags={"environment": "dev"}),
             SimpleNamespace(tags={"environment": "prod"}),
             SimpleNamespace(tags={"environment": "dev"})]
    with mock.patch.object(state_reader, "load_state", return_value={"resources": []}), \
         mock.patch.object(state_reader, "get_instances", return_value=insts):
        workspaces = state_reader.get_workspaces()
    # current workspace "default" is appended since no env tag equals it
    assert [w["name"] for w in workspaces] == ["dev", "prod", "default"]
    assert workspaces[0]["instance_count"] == 2
    assert workspaces[0]["is_current"] is False
    default = [w for w in workspaces if w["name"] == "default"][0]
    assert default["is_current"] is True


def test_get_workspaces_fallback_when_state_unreadable():
    with mock.patch.object(state_reader, "load_state", side_effect=OSError("no")):
        workspaces = state_reader.get_workspaces()
    assert workspaces == [{"name": "default", "is_current": True, "instance_count": 0}]


def test_get_workspaces_default_when_no_env_tags():
    with mock.patch.object(state_reader, "load_state", return_value={"resources": []}), \
         mock.patch.object(state_reader, "get_instances", return_value=[]):
        workspaces = state_reader.get_workspaces()
    assert workspaces[0]["name"] == "default"
    assert workspaces[0]["is_current"] is True


def test_get_workspaces_tf_workspace_env(monkeypatch):
    monkeypatch.setenv("TF_WORKSPACE", "staging")
    insts = [SimpleNamespace(tags={"environment": "dev"})]
    with mock.patch.object(state_reader, "load_state", return_value={"resources": []}), \
         mock.patch.object(state_reader, "get_instances", return_value=insts):
        workspaces = state_reader.get_workspaces()
    names = [w["name"] for w in workspaces]
    # staging is the current workspace and is appended because it's not in env tags
    assert "staging" in names
    staging = [w for w in workspaces if w["name"] == "staging"][0]
    assert staging["is_current"] is True

