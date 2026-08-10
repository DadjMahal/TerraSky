"""Infrastructure import (§14) + read-only import (§106).

Brings unmanaged servers into the platform from the static inventory that is
already parsed from terraform.tfstate (``state_reader``). Import is:

* **idempotent** — instances already present in ``config_store`` custom
  instances are skipped (matched on native ``instance_id``);
* **additive** — nothing is deleted, ever;
* **read-only by default** (§106) — imported resources are recorded with a
  ``readonly=True`` marker (view-only until the user takes ownership).

A future wizard (§99) can layer per-resource selection on top of
``import_inventory``; the engine stays selection-free today.
"""
from __future__ import annotations

from typing import Any

import config_store
from state_reader import get_instances


def import_inventory(provider: str | None = None, readonly: bool = True) -> dict[str, int]:
    """Import servers from the static inventory into the config store.

    Args:
        provider: restrict to one provider key (None = all).
        readonly: mark imported resources read-only (§106).

    Returns:
        ``{"imported": n, "skipped": n, "errors": n}``.
    """
    instances = get_instances()
    existing = config_store.get_custom_instances()
    existing_ids = {str(i.get("instance_id", "")).strip() for i in existing}

    imported = skipped = errors = 0
    for inst in instances:
        if provider and inst.provider != provider:
            continue
        iid = str(inst.instance_id).strip()
        if not iid:
            skipped += 1  # nothing to key on — skip silently
            continue
        if iid in existing_ids:
            skipped += 1
            continue
        try:
            config_store.add_custom_instance(
                provider=inst.provider,
                instance_id=iid,
                name=inst.name or inst.slug,
                region=inst.region or "",
                instance_type=inst.instance_type or "",
                readonly=readonly,
            )
            imported += 1
        except Exception:  # noqa: BLE001 - keep importing the rest
            errors += 1
    return {"imported": imported, "skipped": skipped, "errors": errors}


def imported_count() -> int:
    """Number of custom instances currently marked read-only (§106)."""
    return len([i for i in config_store.get_custom_instances() if i.get("readonly")])
