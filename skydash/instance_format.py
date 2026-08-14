"""Instance data formatting helpers for SkyDash templates.

Every value shown in index.html, detail.html, and instances.html should flow
through these helpers so that:

  * No field ever renders an empty em-dash ``—`` — unknown / missing values
    become ``"N/A"`` instead.
  * Hardware data (CPU / RAM) is back-filled from the ``instance_specs``
    lookup table when Terraform state has gaps (AWS persists neither OS nor
    RAM; Azure persists neither CPU nor RAM).
  * OS is enriched from tags (e.g. ``os``, ``image``, ``ami``) and from the
    DigitalOcean ``image`` field / Azure source-image ``offer`` before falling
    back to ``N/A``.

Usage in Jinja2 (registered via ``app.py`` context processor):

    {{ format_type(inst) }}
    {{ format_region(inst) }}
    {{ format_os(inst) }}
    {{ format_zone(inst) }}
    {{ format_disk(inst) }}
    {{ format_created(inst) }}
    {{ format_status(inst) }}
"""
from __future__ import annotations

from instance_specs import enrich_instance

_NA = "N/A"


def _val(d: dict, key: str) -> str:
    """Return ``d[key]`` as a stripped string, or ``""`` if missing/falsy."""
    v = d.get(key)
    if v is None:
        return ""
    return str(v).strip()


def _is_na_or_empty(v: str) -> bool:
    return v == "" or v == "—" or v == "--"


# ---------------------------------------------------------------------------
# OS detection
# ---------------------------------------------------------------------------

_OS_ALIASES = {
    "ubuntu-24_04-lts": "Ubuntu 24.04 LTS",
    "ubuntu-22_04-lts": "Ubuntu 22.04 LTS",
    "ubuntu-20_04-lts": "Ubuntu 20.04 LTS",
    "ubuntu-24_04": "Ubuntu 24.04 LTS",
    "ubuntu-22_04": "Ubuntu 22.04 LTS",
    "ubuntu-20_04": "Ubuntu 20.04 LTS",
    "ubuntu-18_04-lts": "Ubuntu 18.04 LTS",
    "ubuntu-18_04": "Ubuntu 18.04 LTS",
    "ubuntu": "Ubuntu Linux",
    "amzn2": "Amazon Linux 2",
    "amzn": "Amazon Linux",
    "centos-8": "CentOS 8 Linux",
    "centos-7": "CentOS 7 Linux",
    "centos": "CentOS Linux",
    "rhel-9": "Red Hat Enterprise Linux 9",
    "rhel-8": "Red Hat Enterprise Linux 8",
    "rhel": "Red Hat Enterprise Linux",
    "rocky-9": "Rocky Linux 9",
    "rocky-8": "Rocky Linux 8",
    "rocky": "Rocky Linux",
    "almalinux-9": "AlmaLinux 9",
    "almalinux-8": "AlmaLinux 8",
    "almalinux": "AlmaLinux",
    "debian-12": "Debian 12 Linux",
    "debian-11": "Debian 11 Linux",
    "debian-10": "Debian 10 Linux",
    "debian": "Debian Linux",
    "windows-2022": "Windows Server 2022",
    "windows-2019": "Windows Server 2019",
    "windows-2016": "Windows Server 2016",
    "windows": "Windows Server",
    "win": "Windows Server",
}


def _prettify_os_tag(raw: str) -> str:
    """Turn a raw OS / image string from tags into a friendly label."""
    low = raw.lower().strip()
    for alias, pretty in _OS_ALIASES.items():
        if low.startswith(alias):
            return pretty
    return raw.strip().title() or _NA


def format_os(inst: dict) -> str:
    """Return a human-readable OS label, enriching from tags/state when needed."""
    os_val = _val(inst, "os")
    if os_val:
        return os_val

    tags = inst.get("tags") or {}
    if isinstance(tags, dict):
        # Try common tag keys that carry OS info
        for key in ("os", "image", "ami", "os_name", "operating_system",
                     "image_name", "vm_image", "base_image"):
            v = tags.get(key)
            if v:
                return _prettify_os_tag(str(v))

        # DigitalOcean stores the image slug in `image` tag sometimes
        img = tags.get("image")
        if img:
            return _prettify_os_tag(str(img))

    # Check `extra` dict for source_image_reference (Azure) etc.
    extra = inst.get("extra") or {}
    if isinstance(extra, dict):
        sir = extra.get("source_image_reference")
        if isinstance(sir, dict):
            offer = (sir.get("offer") or "").strip()
            if offer:
                return _prettify_os_tag(offer)

    return _NA


# ---------------------------------------------------------------------------
# Hardware enrichment (CPU / RAM)
# ---------------------------------------------------------------------------

def _enrich_hardware(inst: dict) -> tuple[str, str]:
    """Back-fill CPU/RAM from the instance_specs table."""
    provider = _val(inst, "provider")
    instance_type = _val(inst, "instance_type")
    current_cpu = _val(inst, "cpu")
    current_ram = _val(inst, "ram")
    cpu, ram = enrich_instance(provider, instance_type, current_cpu, current_ram)
    return cpu or _NA, ram or _NA


def format_cpu(inst: dict) -> str:
    """Return the CPU spec string, enriched from the lookup table."""
    cpu, _ = _enrich_hardware(inst)
    return cpu


def format_ram(inst: dict) -> str:
    """Return the RAM spec string, enriched from the lookup table."""
    _, ram = _enrich_hardware(inst)
    return ram


# ---------------------------------------------------------------------------
# Field formatters
# ---------------------------------------------------------------------------

def format_type(inst: dict) -> str:
    """Instance type / size (e.g. ``t3.medium``)."""
    v = _val(inst, "instance_type")
    return v if v else _NA


def format_region(inst: dict) -> str:
    """Cloud region (e.g. ``us-east-1``)."""
    v = _val(inst, "region")
    return v if v else _NA


def format_zone(inst: dict) -> str:
    """Availability zone (e.g. ``us-east-1a``)."""
    v = _val(inst, "availability_zone")
    return v if v else _NA


def format_disk(inst: dict) -> str:
    """Root disk size (e.g. ``50 GB``)."""
    v = _val(inst, "disk_size")
    return v if v else _NA


def format_created(inst: dict) -> str:
    """Creation / launch timestamp."""
    v = _val(inst, "creation_date")
    return v if v else _NA


def format_status(inst: dict) -> str:
    """Normalized status label (capitalized)."""
    v = _val(inst, "status")
    if _is_na_or_empty(v):
        return _NA
    return v.capitalize()


def format_display_name(inst: dict) -> str:
    """Return the display name, falling back to the canonical name."""
    v = _val(inst, "display_name")
    if v:
        return v
    v = _val(inst, "name")
    return v if v else _NA


def format_instance_id(inst: dict) -> str:
    """Provider-native instance identifier."""
    v = _val(inst, "instance_id")
    return v if v else _NA


def format_public_ip(inst: dict) -> str:
    """Public IP address."""
    v = _val(inst, "public_ip")
    return v if v else _NA


def format_private_ip(inst: dict) -> str:
    """Private IP address."""
    v = _val(inst, "private_ip")
    return v if v else _NA


def format_public_dns(inst: dict) -> str:
    """Public DNS name."""
    v = _val(inst, "public_dns")
    return v if v else _NA


def format_private_dns(inst: dict) -> str:
    """Private DNS name."""
    v = _val(inst, "private_dns")
    return v if v else _NA


def format_address(inst: dict) -> str:
    """Terraform resource address (type.name)."""
    v = _val(inst, "address")
    return v if v else _NA


# ---------------------------------------------------------------------------
# Convenience: full formatted dict
# ---------------------------------------------------------------------------

def format_instance(inst: dict) -> dict:
    """Return a dict with every field formatted for display.

    Useful when a template wants all fields pre-formatted in one pass.
    """
    if inst is None:
        inst = {}
    return {
        "name": format_display_name(inst),
        "display_name": format_display_name(inst),
        "provider": _val(inst, "provider_label") or _val(inst, "provider").title() or _NA,
        "provider_key": _val(inst, "provider") or _NA,
        "instance_type": format_type(inst),
        "region": format_region(inst),
        "availability_zone": format_zone(inst),
        "os": format_os(inst),
        "cpu": format_cpu(inst),
        "ram": format_ram(inst),
        "disk_size": format_disk(inst),
        "creation_date": format_created(inst),
        "status": format_status(inst),
        "public_ip": format_public_ip(inst),
        "private_ip": format_private_ip(inst),
        "public_dns": format_public_dns(inst),
        "private_dns": format_private_dns(inst),
        "instance_id": format_instance_id(inst),
        "address": format_address(inst),
    }
