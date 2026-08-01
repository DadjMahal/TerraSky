"""Instance-type specifications lookup table.

Terraform state does not persist OS/RAM for AWS or CPU/RAM for Azure. This
module provides a lookup from instance type strings to their CPU (vCPU count)
and RAM (GB) specifications, so the dashboard can always show hardware info
even when the state file has gaps.

Usage:
    from instance_specs import get_specs
    cpu, ram = get_specs("t3.micro")  # -> ("2 vCPU", "1 GB")
"""
from __future__ import annotations


# Common AWS instance types -> (vCPU count, RAM in GB)
_AWS_SPECS: dict[str, tuple[int, float]] = {
    "t3.nano": (2, 0.5),
    "t3.micro": (2, 1.0),
    "t3.small": (2, 2.0),
    "t3.medium": (2, 4.0),
    "t3.large": (2, 8.0),
    "t3.xlarge": (4, 16.0),
    "t3.2xlarge": (8, 32.0),
    "t2.nano": (1, 0.5),
    "t2.micro": (1, 1.0),
    "t2.small": (1, 2.0),
    "t2.medium": (2, 4.0),
    "t2.large": (2, 8.0),
    "t2.xlarge": (4, 16.0),
    "t2.2xlarge": (8, 32.0),
    "m5.large": (2, 8.0),
    "m5.xlarge": (4, 16.0),
    "m5.2xlarge": (8, 32.0),
    "m5.4xlarge": (16, 64.0),
    "m5a.large": (2, 8.0),
    "m5a.xlarge": (4, 16.0),
    "m5a.2xlarge": (8, 32.0),
    "c5.large": (2, 4.0),
    "c5.xlarge": (4, 8.0),
    "c5.2xlarge": (8, 16.0),
    "c5.4xlarge": (16, 32.0),
    "r5.large": (2, 16.0),
    "r5.xlarge": (4, 32.0),
    "r5.2xlarge": (8, 64.0),
}

# Common Azure VM sizes -> (vCPU count, RAM in GB)
_AZURE_SPECS: dict[str, tuple[int, float]] = {
    "Standard_B1ls": (1, 0.5),
    "Standard_B1s": (1, 1.0),
    "Standard_B1ms": (1, 2.0),
    "Standard_B2s": (2, 4.0),
    "Standard_B2ms": (2, 8.0),
    "Standard_B4ms": (4, 16.0),
    "Standard_B8ms": (8, 32.0),
    "Standard_B2ats_v2": (2, 1.0),
    "Standard_B2pts_v2": (2, 4.0),
    "Standard_B2als_v2": (2, 1.0),
    "Standard_B2pls_v2": (2, 4.0),
    "Standard_B2as_v2": (2, 1.0),
    "Standard_B4ats_v2": (4, 2.0),
    "Standard_B4pts_v2": (4, 8.0),
    "Standard_B4als_v2": (4, 2.0),
    "Standard_B4pls_v2": (4, 8.0),
    "Standard_B4as_v2": (4, 2.0),
    "Standard_B8ats_v2": (8, 4.0),
    "Standard_B8pts_v2": (8, 16.0),
    "Standard_B8als_v2": (8, 4.0),
    "Standard_B8pls_v2": (8, 16.0),
    "Standard_B8as_v2": (8, 4.0),
    "Standard_B16ats_v2": (16, 8.0),
    "Standard_B16pts_v2": (16, 32.0),
    "Standard_B16als_v2": (16, 8.0),
    "Standard_B16pls_v2": (16, 32.0),
    "Standard_B16as_v2": (16, 8.0),
    "Standard_D2s_v3": (2, 8.0),
    "Standard_D4s_v3": (4, 16.0),
    "Standard_D8s_v3": (8, 32.0),
    "Standard_D2s_v5": (2, 8.0),
    "Standard_D4s_v5": (4, 16.0),
    "Standard_F2s_v2": (2, 4.0),
    "Standard_F4s_v2": (4, 8.0),
    "Standard_E2s_v3": (2, 16.0),
    "Standard_E4s_v3": (4, 32.0),
}

# Common Oracle Cloud shapes -> (vCPU count, RAM in GB)
_ORACLE_SPECS: dict[str, tuple[int, float]] = {
    "VM.Standard.E2.1.Micro": (1, 1.0),
    "VM.Standard.E2.1": (1, 8.0),
    "VM.Standard.E2.2": (2, 16.0),
    "VM.Standard.E2.4": (4, 32.0),
    "VM.Standard.A1.Flex": (4, 24.0),  # flexible; default assumption
    "VM.Standard.E3.Flex": (2, 32.0),  # flexible; default assumption
    "VM.Standard2.1": (1, 15.0),
    "VM.Standard2.2": (2, 30.0),
    "VM.Standard2.4": (4, 60.0),
}

# Common Alibaba Cloud instance types -> (vCPU count, RAM in GB)
_ALIBABA_SPECS: dict[str, tuple[int, float]] = {
    "ecs.t6-c1m1.large": (2, 2.0),
    "ecs.t6-c2m1.large": (2, 1.0),
    "ecs.s6-c1m1.small": (1, 1.0),
    "ecs.s6-c1m2.small": (1, 2.0),
    "ecs.n4.small": (1, 1.0),
    "ecs.n4.large": (2, 4.0),
    "ecs.sn1ne.large": (2, 8.0),
    "ecs.sn1ne.xlarge": (4, 16.0),
    "ecs.sn2ne.large": (2, 8.0),
    "ecs.sn2ne.xlarge": (4, 16.0),
    "ecs.g6.large": (2, 8.0),
    "ecs.g6.xlarge": (4, 16.0),
    "ecs.c6.large": (2, 4.0),
    "ecs.c6.xlarge": (4, 8.0),
}

# Merged lookup, keyed by (provider, instance_type)
_ALL_SPECS: dict[str, dict[str, tuple[int, float]]] = {
    "aws": _AWS_SPECS,
    "azure": _AZURE_SPECS,
    "oracle": _ORACLE_SPECS,
    "alibaba": _ALIBABA_SPECS,
}


def get_specs(provider: str, instance_type: str) -> tuple[str, str]:
    """Return (cpu_string, ram_string) for the given provider + instance type.

    Falls back to an empty tuple pair ("", "") if the type is unknown.
    """
    specs = _ALL_SPECS.get(provider, {})
    match = specs.get(instance_type)
    if not match:
        # Try a case-insensitive match as a fallback (Azure names are case-sensitive
        # in the API but state may vary).
        for key, val in specs.items():
            if key.lower() == instance_type.lower():
                match = val
                break
    if not match:
        return "", ""
    vcpu, ram_gb = match
    cpu = f"{vcpu} vCPU"
    ram = f"{ram_gb:g} GB"
    return cpu, ram


def enrich_instance(provider: str, instance_type: str, current_cpu: str, current_ram: str) -> tuple[str, str]:
    """Fill in missing CPU/RAM from the specs table.

    Only replaces empty values; existing values from Terraform state are kept.
    """
    if current_cpu and current_ram:
        return current_cpu, current_ram
    cpu, ram = get_specs(provider, instance_type)
    return (current_cpu or cpu, current_ram or ram)
