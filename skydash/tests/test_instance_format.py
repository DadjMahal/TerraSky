"""Tests for instance_format — Jinja field formatters (N/A fallbacks, OS
detection, hardware enrichment, full format_instance dict).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instance_format import (
    format_type,
    format_region,
    format_zone,
    format_disk,
    format_created,
    format_status,
    format_display_name,
    format_instance_id,
    format_public_ip,
    format_private_ip,
    format_public_dns,
    format_private_dns,
    format_address,
    format_os,
    format_cpu,
    format_ram,
    format_instance,
    _val,
    _is_na_or_empty,
    _prettify_os_tag,
)

# --------------------------------------------------------------------------- #
# _val / _is_na_or_empty helpers                                              #
# --------------------------------------------------------------------------- #
def test_val_returns_stripped_string():
    assert _val({"os": "  Ubuntu  "}, "os") == "Ubuntu"


def test_val_missing_key_returns_empty():
    assert _val({}, "os") == ""


def test_val_none_value_returns_empty():
    assert _val({"os": None}, "os") == ""


def test_is_na_or_empty_true_cases():
    assert _is_na_or_empty("") is True
    assert _is_na_or_empty("—") is True
    assert _is_na_or_empty("--") is True


def test_is_na_or_empty_false_cases():
    assert _is_na_or_empty("running") is False
    assert _is_na_or_empty("N/A") is False


# --------------------------------------------------------------------------- #
# Field formatters — N/A fallback                                             #
# --------------------------------------------------------------------------- #
def test_format_type_present():
    assert format_type({"instance_type": "t3.medium"}) == "t3.medium"


def test_format_type_missing():
    assert format_type({}) == "N/A"


def test_format_region_present():
    assert format_region({"region": "us-east-1"}) == "us-east-1"


def test_format_region_missing():
    assert format_region({}) == "N/A"


def test_format_zone_present():
    assert format_zone({"availability_zone": "us-east-1a"}) == "us-east-1a"


def test_format_zone_missing():
    assert format_zone({}) == "N/A"


def test_format_disk_present():
    assert format_disk({"disk_size": "50 GB"}) == "50 GB"


def test_format_disk_missing():
    assert format_disk({}) == "N/A"


def test_format_created_present():
    assert format_created({"creation_date": "2024-01-15T10:00:00Z"}) == "2024-01-15T10:00:00Z"


def test_format_created_missing():
    assert format_created({}) == "N/A"


def test_format_status_normalizes():
    assert format_status({"status": "running"}) == "Running"
    assert format_status({"status": "STOPPED"}) == "Stopped"


def test_format_status_empty_becomes_na():
    assert format_status({"status": ""}) == "N/A"


def test_format_status_dash_becomes_na():
    assert format_status({"status": "—"}) == "N/A"


def test_format_display_name_present():
    assert format_display_name({"display_name": "web-1"}) == "web-1"


def test_format_display_name_falls_back_to_name():
    assert format_display_name({"name": "web-1"}) == "web-1"


def test_format_display_name_missing_both():
    assert format_display_name({}) == "N/A"


def test_format_instance_id_present():
    assert format_instance_id({"instance_id": "i-1234"}) == "i-1234"


def test_format_instance_id_missing():
    assert format_instance_id({}) == "N/A"


def test_format_public_ip_present():
    assert format_public_ip({"public_ip": "1.2.3.4"}) == "1.2.3.4"


def test_format_public_ip_missing():
    assert format_public_ip({}) == "N/A"


def test_format_private_ip_present():
    assert format_private_ip({"private_ip": "10.0.0.1"}) == "10.0.0.1"


def test_format_private_ip_missing():
    assert format_private_ip({}) == "N/A"


def test_format_public_dns_present():
    assert format_public_dns({"public_dns": "ec2.amazonaws.com"}) == "ec2.amazonaws.com"


def test_format_public_dns_missing():
    assert format_public_dns({}) == "N/A"


def test_format_private_dns_present():
    assert format_private_dns({"private_dns": "ip-10-0-0-1.ec2"}) == "ip-10-0-0-1.ec2"


def test_format_private_dns_missing():
    assert format_private_dns({}) == "N/A"


def test_format_address_present():
    assert format_address({"address": "aws_instance.web"}) == "aws_instance.web"


def test_format_address_missing():
    assert format_address({}) == "N/A"


# --------------------------------------------------------------------------- #
# OS detection                                                                #
# --------------------------------------------------------------------------- #
def test_format_os_direct_value():
    assert format_os({"os": "Ubuntu 22.04 LTS"}) == "Ubuntu 22.04 LTS"


def test_format_os_from_tag_os():
    inst = {"tags": {"os": "ubuntu-22_04-lts"}}
    assert format_os(inst) == "Ubuntu 22.04 LTS"


def test_format_os_from_tag_ami():
    inst = {"tags": {"ami": "amzn2"}}
    assert format_os(inst) == "Amazon Linux 2"


def test_format_os_from_tag_image():
    inst = {"tags": {"image": "centos-8"}}
    assert format_os(inst) == "CentOS 8 Linux"


def test_format_os_from_extra_source_image_reference():
    inst = {"extra": {"source_image_reference": {"offer": "windows-2022"}}}
    assert format_os(inst) == "Windows Server 2022"


def test_format_os_fallback_na():
    assert format_os({}) == "N/A"


def test_format_os_unknown_tag_value_titles():
    inst = {"tags": {"os": "custom-linux"}}
    assert format_os(inst) == "Custom-Linux"


def test_format_os_tags_none():
    assert format_os({"tags": None}) == "N/A"


def test_format_os_tags_not_dict():
    """If tags is not a dict, falls through to extra / N/A."""
    assert format_os({"tags": "not-a-dict"}) == "N/A"


# --------------------------------------------------------------------------- #
# Hardware enrichment (CPU / RAM)                                             #
# --------------------------------------------------------------------------- #
def test_format_cpu_from_specs():
    inst = {"provider": "aws", "instance_type": "t3.small"}
    assert format_cpu(inst) == "2 vCPU"


def test_format_ram_from_specs():
    inst = {"provider": "aws", "instance_type": "t3.small"}
    assert format_ram(inst) == "2 GB"


def test_format_cpu_overridden_by_existing_value():
    inst = {"provider": "aws", "instance_type": "t3.small", "cpu": "4 vCPU"}
    assert format_cpu(inst) == "4 vCPU"


def test_format_ram_overridden_by_existing_value():
    inst = {"provider": "aws", "instance_type": "t3.small", "ram": "16 GB"}
    assert format_ram(inst) == "16 GB"


def test_format_cpu_unknown_type_returns_na():
    inst = {"provider": "aws", "instance_type": "t99.unknown"}
    assert format_cpu(inst) == "N/A"


def test_format_ram_unknown_type_returns_na():
    inst = {"provider": "aws", "instance_type": "t99.unknown"}
    assert format_ram(inst) == "N/A"


def test_format_cpu_azure():
    inst = {"provider": "azure", "instance_type": "Standard_D4s_v3"}
    assert format_cpu(inst) == "4 vCPU"


# --------------------------------------------------------------------------- #
# _prettify_os_tag                                                            #
# --------------------------------------------------------------------------- #
def test_prettify_os_tag_known_alias():
    assert _prettify_os_tag("ubuntu-24_04-lts") == "Ubuntu 24.04 LTS"


def test_prettify_os_tag_amzn2():
    assert _prettify_os_tag("amzn2") == "Amazon Linux 2"


def test_prettify_os_tag_unknown():
    assert _prettify_os_tag("my-distro") == "My-Distro"


def test_prettify_os_tag_empty():
    assert _prettify_os_tag("") == "N/A"


# --------------------------------------------------------------------------- #
# format_instance — full dict                                                #
# --------------------------------------------------------------------------- #
def test_format_instance_full_dict():
    inst = {
        "name": "web-1",
        "display_name": "Web Server",
        "provider": "aws",
        "instance_type": "t3.medium",
        "region": "us-east-1",
        "availability_zone": "us-east-1a",
        "cpu": "",
        "ram": "",
        "disk_size": "20 GB",
        "creation_date": "2024-01-15T10:00:00Z",
        "status": "running",
        "public_ip": "1.2.3.4",
        "private_ip": "10.0.0.1",
        "public_dns": "ec2.pub",
        "private_dns": "ec2.priv",
        "instance_id": "i-1234",
        "address": "aws_instance.web",
        "os": "Ubuntu 22.04 LTS",
    }
    result = format_instance(inst)
    assert result["name"] == "Web Server"
    assert result["display_name"] == "Web Server"
    assert result["provider"] == "Aws"
    assert result["provider_key"] == "aws"
    assert result["instance_type"] == "t3.medium"
    assert result["region"] == "us-east-1"
    assert result["availability_zone"] == "us-east-1a"
    assert result["cpu"] == "2 vCPU"
    assert result["ram"] == "4 GB"
    assert result["disk_size"] == "20 GB"
    assert result["creation_date"] == "2024-01-15T10:00:00Z"
    assert result["status"] == "Running"
    assert result["public_ip"] == "1.2.3.4"
    assert result["private_ip"] == "10.0.0.1"
    assert result["public_dns"] == "ec2.pub"
    assert result["private_dns"] == "ec2.priv"
    assert result["instance_id"] == "i-1234"
    assert result["address"] == "aws_instance.web"


def test_format_instance_none_input():
    result = format_instance(None)
    assert result["name"] == "N/A"
    assert result["instance_type"] == "N/A"
    assert result["provider"] == "N/A"
    assert result["cpu"] == "N/A"


def test_format_instance_empty_dict():
    result = format_instance({})
    assert result["name"] == "N/A"
    assert result["status"] == "N/A"
    assert result["os"] == "N/A"
    assert result["cpu"] == "N/A"
    assert result["ram"] == "N/A"


def test_format_instance_provider_label_fallback():
    inst = {"provider": "azure", "name": "test"}
    result = format_instance(inst)
    assert result["provider"] == "Azure"


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
