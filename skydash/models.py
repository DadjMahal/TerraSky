"""Shared, provider-independent data model for cloud instances.

The :class:`Instance` dataclass is the single representation used across the
dashboard, the detail page and the provider implementations. Every cloud
provider maps its native attributes onto this model so that business logic
never depends on a specific provider's schema (see SPEC.md "Architecture Goals").
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

# Normalized provider keys (independent of the Terraform provider source string).
AWS = "aws"
AZURE = "azure"
ORACLE = "oracle"
ALIBABA = "alibaba"
DIGITALOCEAN = "digitalocean"

# Bootstrap Icons used in the UI, keyed by normalized provider key.
PROVIDER_ICONS = {
    AWS: "bi-amazon",
    AZURE: "bi-microsoft",
    ORACLE: "bi-cloud-fill",
    ALIBABA: "bi-cloud",
    DIGITALOCEAN: "bi-server",
}

# Human readable labels for providers.
PROVIDER_LABELS = {
    AWS: "AWS",
    AZURE: "Azure",
    ORACLE: "Oracle Cloud",
    ALIBABA: "Alibaba Cloud",
    DIGITALOCEAN: "DigitalOcean",
}

# Normalized status values displayed throughout the UI.
STATUS_RUNNING = "running"
STATUS_STOPPED = "stopped"
STATUS_STARTING = "starting"
STATUS_STOPPING = "stopping"
STATUS_ERROR = "error"
STATUS_UNKNOWN = "unknown"
STATUS_LOADING = "loading"


def slugify(value: str) -> str:
    """Convert an arbitrary string into a URL-safe slug (lower-case, hyphenated)."""
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


@dataclass
class Instance:
    """Provider-independent representation of a cloud instance."""

    # Identity
    slug: str = ""               # stable URL slug, e.g. "aws-hermes"
    name: str = ""               # canonical Terraform resource name
    display_name: str = ""       # provider-visible name (may differ from `name`)
    provider: str = ""           # normalized provider key
    provider_label: str = ""     # human readable provider name
    instance_id: str = ""        # provider-native instance identifier
    address: str = ""            # Terraform resource address (type.name)

        # Static inventory metadata (read from terraform.tfstate)
    region: str = ""
    availability_zone: str = ""
    instance_type: str = ""
    public_ip: str = ""
    private_ip: str = ""
    public_dns: str = ""
    private_dns: str = ""
    os: str = ""
    cpu: str = ""
    ram: str = ""
    disk_size: str = ""
    creation_date: str = ""
    tags: dict = field(default_factory=dict)

    # Security group / firewall IDs (or names) attached to the instance,
    # sourced from Terraform state. Used by providers.get_security_groups()
    # as the lookup hint for fetching live inbound/outbound rules (§Task 4).
    security_groups: list = field(default_factory=list)

    # Runtime state (filled live by provider implementations)
    status: str = STATUS_UNKNOWN
    can_manage: bool = False
    error: str = ""

    # Provider-specific helpers kept for the provider implementations only.
    extra: dict = field(default_factory=dict)

    @property
    def icon(self) -> str:
        return PROVIDER_ICONS.get(self.provider, "bi-question-circle")

    def to_dict(self) -> dict:
        """Serialize to a plain dict for templates and JSON endpoints."""
        data = asdict(self)
        data["icon"] = self.icon
        return data
