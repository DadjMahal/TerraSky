"""Tests for instance_specs — CPU/RAM lookup tables (§hardware enrichment).

Pure stdlib. Covers AWS, Azure, Oracle, Alibaba, DigitalOcean lookups,
case-insensitive fallback, and the enrich_instance back-fill logic.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instance_specs import get_specs, enrich_instance


# --------------------------------------------------------------------------- #
# get_specs — direct lookup                                                    #
# --------------------------------------------------------------------------- #
def test_get_specs_aws_t3_micro():
    cpu, ram = get_specs("aws", "t3.micro")
    assert cpu == "2 vCPU"
    assert ram == "1 GB"


def test_get_specs_aws_t3_large():
    cpu, ram = get_specs("aws", "t3.large")
    assert cpu == "2 vCPU"
    assert ram == "8 GB"


def test_get_specs_aws_t3_2xlarge():
    cpu, ram = get_specs("aws", "t3.2xlarge")
    assert cpu == "8 vCPU"
    assert ram == "32 GB"


def test_get_specs_aws_m5_4xlarge():
    cpu, ram = get_specs("aws", "m5.4xlarge")
    assert cpu == "16 vCPU"
    assert ram == "64 GB"


def test_get_specs_aws_c5_2xlarge():
    cpu, ram = get_specs("aws", "c5.2xlarge")
    assert cpu == "8 vCPU"
    assert ram == "16 GB"


def test_get_specs_aws_r5_2xlarge():
    cpu, ram = get_specs("aws", "r5.2xlarge")
    assert cpu == "8 vCPU"
    assert ram == "64 GB"


def test_get_specs_azure_standard_b2s():
    cpu, ram = get_specs("azure", "Standard_B2s")
    assert cpu == "2 vCPU"
    assert ram == "4 GB"


def test_get_specs_azure_standard_d4s_v3():
    cpu, ram = get_specs("azure", "Standard_D4s_v3")
    assert cpu == "4 vCPU"
    assert ram == "16 GB"


def test_get_specs_oracle_e2_1_micro():
    cpu, ram = get_specs("oracle", "VM.Standard.E2.1.Micro")
    assert cpu == "1 vCPU"
    assert ram == "1 GB"


def test_get_specs_alibaba_g6_xlarge():
    cpu, ram = get_specs("alibaba", "ecs.g6.xlarge")
    assert cpu == "4 vCPU"
    assert ram == "16 GB"


def test_get_specs_digitalocean_s_4vcpu_16gb():
    cpu, ram = get_specs("digitalocean", "s-4vcpu-16gb")
    assert cpu == "4 vCPU"
    assert ram == "16 GB"


# --------------------------------------------------------------------------- #
# get_specs — edge cases                                                      #
# --------------------------------------------------------------------------- #
def test_get_specs_unknown_provider_returns_empty():
    cpu, ram = get_specs("gcp", "n1-standard-1")
    assert cpu == ""
    assert ram == ""


def test_get_specs_unknown_instance_type_returns_empty():
    cpu, ram = get_specs("aws", "t99.unknown")
    assert cpu == ""
    assert ram == ""


def test_get_specs_case_insensitive_fallback_azure():
    """Azure names are case-sensitive in the API but state may vary."""
    cpu, ram = get_specs("azure", "standard_b2s")
    assert cpu == "2 vCPU"
    assert ram == "4 GB"


def test_get_specs_case_insensitive_fallback_uppercase():
    cpu, ram = get_specs("aws", "T3.MICRO")
    assert cpu == "2 vCPU"
    assert ram == "1 GB"


def test_get_specs_case_insensitive_fallback_alibaba():
    cpu, ram = get_specs("alibaba", "ECS.G6.XLARGE")
    assert cpu == "4 vCPU"
    assert ram == "16 GB"


# --------------------------------------------------------------------------- #
# enrich_instance — back-fill logic                                           #
# --------------------------------------------------------------------------- #
def test_enrich_instance_keeps_existing_values():
    """When both CPU and RAM are already present, they are preserved."""
    cpu, ram = enrich_instance("aws", "t3.micro", "4 vCPU", "8 GB")
    assert cpu == "4 vCPU"
    assert ram == "8 GB"


def test_enrich_instance_fills_both_missing():
    cpu, ram = enrich_instance("aws", "t3.medium", "", "")
    assert cpu == "2 vCPU"
    assert ram == "4 GB"


def test_enrich_instance_fills_cpu_only():
    cpu, ram = enrich_instance("aws", "t3.large", "", "8 GB")
    assert cpu == "2 vCPU"
    assert ram == "8 GB"


def test_enrich_instance_fills_ram_only():
    cpu, ram = enrich_instance("aws", "t3.large", "2 vCPU", "")
    assert cpu == "2 vCPU"
    assert ram == "8 GB"


def test_enrich_instance_unknown_type_returns_empty_strings():
    cpu, ram = enrich_instance("aws", "t99.unknown", "", "")
    assert cpu == ""
    assert ram == ""


def test_enrich_instance_unknown_provider_returns_empty_when_missing():
    """If provider not in the table and values are empty, returns empty."""
    cpu, ram = enrich_instance("gcp", "n1-standard-1", "", "")
    assert cpu == ""
    assert ram == ""


def test_enrich_instance_partially_filled_unknown_type():
    """If the instance type is unknown but CPU was already set, RAM stays empty."""
    cpu, ram = enrich_instance("aws", "t99.unknown", "2 vCPU", "")
    assert cpu == "2 vCPU"
    assert ram == ""


def test_enrich_instance_azure_backfill():
    cpu, ram = enrich_instance("azure", "Standard_D2s_v3", "", "")
    assert cpu == "2 vCPU"
    assert ram == "8 GB"


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
