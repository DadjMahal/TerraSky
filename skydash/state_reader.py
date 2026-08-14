"""Reads the local Terraform state file and maps resources onto the
provider-independent :class:`Instance` model.

Only *static* inventory data (metadata persisted in ``terraform.tfstate``) is
extracted here. Live power state is fetched on demand by the provider
implementations in the :mod:`providers` package, keeping this module free of any
cloud SDK dependency.
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

from models import (
    ALIBABA,
    AWS,
    AZURE,
    DIGITALOCEAN,
    Instance,
    ORACLE,
    PROVIDER_LABELS,
    slugify,
)
from instance_specs import enrich_instance

TERRAFORM_DIR = os.environ.get("TERRAFORM_DIR", "/home/volodro/terraform")
STATE_FILE = os.path.join(TERRAFORM_DIR, "terraform.tfstate")

# Terraform resource type -> normalized provider key.
RESOURCE_TYPE_PROVIDER = {
    "aws_instance": AWS,
    "azurerm_linux_virtual_machine": AZURE,
    "azurerm_windows_virtual_machine": AZURE,
    "oci_core_instance": ORACLE,
    "alicloud_instance": ALIBABA,
    "digitalocean_droplet": DIGITALOCEAN,
}


def load_state() -> dict:
    """Load and parse the Terraform state file."""
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def _first(items, default=None):
    """Return the first element of a list-like value, or `default`."""
    if isinstance(items, list) and items:
        return items[0]
    return default


def _s(value, default: str = "") -> str:
    return "" if value is None else str(value)


# --- Per-provider attribute mappers ------------------------------------------

def _map_aws(attrs: dict) -> dict:
    # AWS does not persist OS, RAM or launch time in state; CPU comes from
    # cpu_options (core_count * threads_per_core) and disk from root_block_device.
    cpu_opts = _first(attrs.get("cpu_options") or [])
    vcpu = ""
    if isinstance(cpu_opts, dict):
        cc = cpu_opts.get("core_count") or 0
        tp = cpu_opts.get("threads_per_core") or 0
        if cc and tp:
            vcpu = f"{int(cc) * int(tp)} vCPU"
    rbd = _first(attrs.get("root_block_device") or [])
    disk = ""
    if isinstance(rbd, dict) and rbd.get("volume_size"):
        disk = f"{rbd.get('volume_size')} GB"
    return dict(
        display_name=(attrs.get("tags") or {}).get("Name", ""),
        instance_type=attrs.get("instance_type", ""),
        region=attrs.get("region", ""),
        availability_zone=attrs.get("availability_zone", ""),
        public_ip=attrs.get("public_ip", ""),
        private_ip=attrs.get("private_ip", ""),
        public_dns=attrs.get("public_dns", ""),
        private_dns=attrs.get("private_dns", ""),
        os="",
        cpu=vcpu,
        ram="",
        disk_size=disk,
        creation_date="",
        tags=attrs.get("tags") or {},
        instance_id=attrs.get("id", ""),
        security_groups=attrs.get("vpc_security_group_ids") or [],
        extra={},
        )


def _azure_os(attrs: dict) -> str:
    # Derive a friendly OS label from the source image reference when available.
    ref = _first(attrs.get("source_image_reference") or [])
    if isinstance(ref, dict):
        offer = ref.get("offer", "")
        mapping = {
            "ubuntu-24_04-lts": "Ubuntu 24.04 LTS",
            "ubuntu-22_04-lts": "Ubuntu 22.04 LTS",
        }
        return mapping.get(offer, offer or _s(ref.get("publisher")))
    return ""


def _map_azure(attrs: dict) -> dict:
    # Azure keeps the VM name and resource group in state; both are required to
    # query the live power state and to start/stop the VM.
    osd = _first(attrs.get("os_disk") or [])
    disk = ""
    if isinstance(osd, dict) and osd.get("disk_size_gb"):
        disk = f"{osd.get('disk_size_gb')} GB"
    zone = attrs.get("zone")
    return dict(
        display_name=attrs.get("name", ""),
        instance_type=attrs.get("size", ""),
        region=attrs.get("location", ""),
        availability_zone=f"Zone {zone}" if zone else "",
        public_ip=attrs.get("public_ip_address", ""),
        private_ip=attrs.get("private_ip_address", ""),
        public_dns="",
        private_dns="",
        os=_azure_os(attrs),
        cpu="",
        ram="",
        disk_size=disk,
        creation_date="",
        tags=attrs.get("tags") or {},
        instance_id=attrs.get("id", ""),
        extra={
            "resource_group_name": attrs.get("resource_group_name", ""),
            "vm_name": attrs.get("name", ""),
        },
        security_groups=[],
    )


def _map_oracle(attrs: dict) -> dict:
    # OCI exposes OCPUs and memory through shape_config; boot volume size lives
    # in source_details.
    sc = _first(attrs.get("shape_config") or [])
    cpu = ram = ""
    if isinstance(sc, dict):
        ocpus = sc.get("ocpus")
        mem = sc.get("memory_in_gbs")
        if ocpus:
            cpu = f"{ocpus:g} vCPU"
        if mem:
            ram = f"{mem:g} GB"
    sd = _first(attrs.get("source_details") or [])
    disk = ""
    if isinstance(sd, dict) and sd.get("boot_volume_size_in_gbs"):
        disk = f"{sd.get('boot_volume_size_in_gbs')} GB"
    return dict(
        display_name=attrs.get("display_name", ""),
        instance_type=attrs.get("shape", ""),
        region=attrs.get("region", ""),
        availability_zone=attrs.get("availability_domain", ""),
        public_ip=attrs.get("public_ip", ""),
        private_ip=attrs.get("private_ip", ""),
        public_dns="",
        private_dns="",
        os="",
        cpu=cpu,
        ram=ram,
        disk_size=disk,
        creation_date=attrs.get("time_created", ""),
        tags=attrs.get("freeform_tags") or {},
        instance_id=attrs.get("id", ""),
        extra={
            # Propagate compartment_id so OracleProvider._get_live_ips can list
            # VNIC attachments in the correct compartment without re-reading config.
            "compartment_id": attrs.get("compartment_id", ""),
        },
    )


def _map_alibaba(attrs: dict) -> dict:
    # Alibaba persists cpu (vCPUs), memory (MB) and system_disk_size (GB).
    cpu = f"{int(attrs['cpu'])} vCPU" if attrs.get("cpu") else ""
    ram = f"{int(attrs['memory']) / 1024:g} GB" if attrs.get("memory") else ""
    zone = attrs.get("availability_zone", "")
    # Region is not stored per instance; derive it from the zone (strip trailing
    # letter) or fall back to the ALICLOUD_REGION environment variable.
    region = zone[:-1] if zone and zone[-1].isalpha() else os.environ.get("ALICLOUD_REGION", "")
    return dict(
        display_name=attrs.get("instance_name", ""),
        instance_type=attrs.get("instance_type", ""),
        region=region,
        availability_zone=zone,
        public_ip=attrs.get("public_ip", ""),
        private_ip=attrs.get("private_ip", ""),
        public_dns="",
        private_dns="",
        os=attrs.get("os_name") or attrs.get("os_type") or "",
        cpu=cpu,
        ram=ram,
        disk_size=f"{attrs.get('system_disk_size')} GB" if attrs.get("system_disk_size") else "",
        creation_date=attrs.get("create_time", ""),
        tags=attrs.get("tags") or {},
        instance_id=attrs.get("id", ""),
        security_groups=list(attrs.get("security_groups") or []),
        extra={},
    )


def _map_digitalocean(attrs: dict) -> dict:
    """Map a ``digitalocean_droplet`` state resource to dashboard fields.

    DigitalOcean Terraform state attributes (flat): ``id``, ``name``, ``size``
    (slug, e.g. ``s-2vcpu-2gb``), ``region`` (slug, e.g. ``nyc3``), ``image``,
    ``ipv4_address``, ``ipv4_address_private``, ``tags`` (list), ``created_at``.
    DO exposes regions, not availability zones. CPU/RAM are back-filled from the
    instance_specs table in ``enrich_instance`` when the size slug is known.
    """
    tags = attrs.get("tags")
    if isinstance(tags, list):
        tags = {t: t for t in tags if t}
    return dict(
        display_name=attrs.get("name", ""),
        instance_type=attrs.get("size", ""),
        region=attrs.get("region", ""),
        availability_zone="",
        public_ip=attrs.get("ipv4_address", ""),
        private_ip=attrs.get("ipv4_address_private", ""),
        public_dns="",
        private_dns="",
        os=attrs.get("image", ""),
        cpu="",
        ram="",
        disk_size="",
        creation_date=attrs.get("created_at", ""),
        tags=tags or {},
        instance_id=str(attrs.get("id", "")) if attrs.get("id") else "",
        security_groups=[],
        extra={},
    )


MAPPERS = {AWS: _map_aws, AZURE: _map_azure, ORACLE: _map_oracle, ALIBABA: _map_alibaba, DIGITALOCEAN: _map_digitalocean}


# --- Public API --------------------------------------------------------------

def _build(res: dict) -> Instance | None:
    rtype = res.get("type", "")
    provider = RESOURCE_TYPE_PROVIDER.get(rtype)
    if not provider:
        return None
    instances = res.get("instances") or []
    if not instances:
        return None
    attrs = instances[0].get("attributes", {}) or {}
    mapped = MAPPERS[provider](attrs)
    # Fill in missing CPU/RAM from the instance-type specs lookup table
    # (AWS state has no RAM/OS; Azure state has no CPU/RAM).
    mapped["cpu"], mapped["ram"] = enrich_instance(
        provider, mapped["instance_type"], mapped["cpu"], mapped["ram"]
    )
    name = res.get("name", "unnamed")
    slug = f"{provider}-{slugify(name)}"
    return Instance(
        slug=slug,
        name=name,
        display_name=mapped["display_name"] or name,
        provider=provider,
        provider_label=PROVIDER_LABELS.get(provider, provider),
        instance_id=mapped["instance_id"],
        address=f"{rtype}.{name}",
        region=mapped["region"],
        availability_zone=mapped["availability_zone"],
        instance_type=mapped["instance_type"],
        public_ip=mapped["public_ip"],
        private_ip=mapped["private_ip"],
        public_dns=mapped["public_dns"],
        private_dns=mapped["private_dns"],
        os=mapped["os"],
        cpu=mapped["cpu"],
        ram=mapped["ram"],
        disk_size=mapped["disk_size"],
        creation_date=mapped["creation_date"],
        tags=mapped["tags"],
        security_groups=mapped.get("security_groups", []),
        extra=mapped["extra"],
    )


def get_instances() -> list[Instance]:
    """Return all managed compute instances found in the Terraform state."""
    try:
        state = load_state()
    except Exception as e:  # pragma: no cover - defensive logging
        print(f"ERROR reading state: {e}", file=sys.stderr)
        return []
    out = []
    for res in state.get("resources", []):
        if res.get("mode") != "managed":
            continue
        inst = _build(res)
        if inst:
            out.append(inst)
    return out


def get_instance_by_slug(slug: str) -> Instance | None:
    """Look up a single instance by its URL slug."""
    for inst in get_instances():
        if inst.slug == slug:
            return inst
    return None


# --- tfstate metadata (§11) ----------------------------------------------------

def tfstate_info() -> dict[str, Any]:
    """Return metadata about the Terraform state file (§11).

    Includes resource count, managed-resource count, terraform version,
    state serial / lineage, and the file's last-modified timestamp.
    Read-only: never raises — returns ``{"available": False}`` on error.
    """
    try:
        state = load_state()
    except Exception:  # pragma: no cover - defensive
        return {"available": False, "error": "state file not readable"}

    resources = state.get("resources", [])
    managed = [r for r in resources if r.get("mode") == "managed"]
    instances = []
    for res in managed:
        if res.get("_build") is not None or res.get("instances"):
            instances.append(res)

    info: dict[str, Any] = {
        "available": True,
        "terraform_version": state.get("version", ""),
        "serial": state.get("serial", 0),
        "lineage": state.get("lineage", ""),
        "resource_count": len(resources),
        "managed_count": len(managed),
        "instance_count": len(get_instances()),
    }

    # Last-modified from the file mtime (§13: state versioning/audit)
    try:
        mtime = os.path.getmtime(STATE_FILE)
        info["last_modified"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime))
        info["last_modified_epoch"] = mtime
    except Exception:
        info["last_modified"] = ""
        info["last_modified_epoch"] = 0

    # Derive a coarse workspace from terraform {workspace dir} or env override
    info["workspace"] = os.environ.get("TF_WORKSPACE", "default")
    return info


# --- Workspaces (§12) ----------------------------------------------------------

def get_workspaces() -> list[dict[str, Any]]:
    """Return workspace/environment names derived from tfstate (§12).

    Terraform workspaces are not stored inside the state JSON itself; the
    canonical workspace is the one that produced this state file. We derive a
    workspace list from:
      1. The ``TF_WORKSPACE`` env var (explicit override).
      2. The ``environment`` tag on each instance (if present).
      3. A ``default`` workspace as fallback.

    Each entry: ``{"name": str, "is_current": bool, "instance_count": int}``.
    """
    try:
        state = load_state()
    except Exception:
        return [{"name": "default", "is_current": True, "instance_count": 0}]

    current_ws = os.environ.get("TF_WORKSPACE", "default")

    # Collect environment tags from all instances
    env_counts: dict[str, int] = {}
    for inst in get_instances():
        env = (inst.tags or {}).get("environment", current_ws)
        env_counts[env] = env_counts.get(env, 0) + 1

    if not env_counts:
        return [{"name": current_ws, "is_current": True, "instance_count": 0}]

    workspaces = []
    for name, count in sorted(env_counts.items()):
        workspaces.append({
            "name": name,
            "is_current": name == current_ws,
            "instance_count": count,
        })
    if not any(w["name"] == current_ws for w in workspaces):
        workspaces.append({"name": current_ws, "is_current": True, "instance_count": 0})
    return workspaces
