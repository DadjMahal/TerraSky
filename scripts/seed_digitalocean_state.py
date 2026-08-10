#!/usr/bin/env python3
"""seed_digitalocean_state.py — onboard your DigitalOcean Droplets into SkyDash.

Calls the DigitalOcean API v2 (GET /v2/droplets, follows all pages) and writes a
`digitalocean_droplet` entry into terraform.tfstate for every Droplet NOT already
present (matched by numeric id).  Running it again is safe/idempotent.  The 7
existing AWS/Azure/Oracle/Alibaba entries are preserved unchanged.

The data written (id, name, size slug, region slug, status, created_at, tags,
public/private IP) is fetched LIVE from your DO account — nothing is fabricated.
Live power-state/start/stop then works via the DigitalOceanProvider once
DIGITALOCEAN_ACCESS_TOKEN is set in terraform/.env.

Usage:
    DIGITALOCEAN_ACCESS_TOKEN=xxxxx \
        /home/volodro/skydash/venv/bin/python /home/volodro/scripts/seed_digitalocean_state.py

After seeding:  sudo systemctl restart skydash
"""
from __future__ import annotations

import json
import os
import sys

import requests

TOKEN = os.environ.get("DIGITALOCEAN_ACCESS_TOKEN", "")
STATE = os.environ.get("SKYDASH_TFSTATE", "/home/volodro/terraform/terraform.tfstate")
API = "https://api.digitalocean.com/v2"
HEADERS = {"Authorization": f"Bearer {TOKEN}",
           "Accept": "application/vnd.digitalocean.v2+json",
           "Content-Type": "application/json"}


def _slug(value: str) -> str:
    """Rough terraform-resource-name sanitizer (must be unique per type)."""
    out = (value or "").strip().lower().replace(" ", "-")
    return "".join(c if (c.isalnum() or c in "-_") else "-" for c in out) or "droplet"


def existing_droplet_ids(state: dict) -> set:
    ids = set()
    for r in state.get("resources", []):
        if r.get("type") == "digitalocean_droplet":
            attrs = (r.get("instances") or [{}])[0].get("attributes", {}) or {}
            if attrs.get("id"):
                ids.add(str(attrs["id"]))
    return ids


def _region_slug(d: dict) -> str:
    region = d.get("region")
    if isinstance(region, dict):
        return region.get("slug", "") or ""
    return region or ""


def _size_slug(d: dict) -> str:
    size = d.get("size")
    if isinstance(size, dict):
        return size.get("slug", "") or ""
    return size or ""


def _image(d: dict) -> str:
    image = d.get("image")
    if isinstance(image, dict):
        return image.get("slug") or image.get("id") or "" or ""
    return image or ""


def _ips(d: dict) -> tuple[str, str]:
    v4 = ((d.get("networks") or {}).get("v4") or []) if isinstance(d.get("networks"), dict) else []
    pub = next((n.get("ip_address") for n in v4 if n.get("type") == "public" and n.get("ip_address")), "")
    priv = next((n.get("ip_address") for n in v4 if n.get("type") == "private" and n.get("ip_address")), "")
    return pub, priv


def droplet_to_resource(d: dict) -> dict:
    pub, priv = _ips(d)
    name = d.get("name", "")
    return {
        "mode": "managed",
        "type": "digitalocean_droplet",
        "name": "drop_%s_%s" % (_slug(name), d.get("id") or "0"),
        "provider": 'provider["registry.terraform.io/digitalocean/digitalocean"]',
        "instances": [{
            "attributes": {
                "id": d.get("id"),
                "name": name,
                "size": _size_slug(d),
                "region": _region_slug(d),
                "image": _image(d),
                "status": d.get("status", ""),
                "ipv4_address": pub,
                "ipv4_address_private": priv,
                "ipv6_address": "",
                "tags": d.get("tags") or [],
                "created_at": d.get("created_at", ""),
                "vcpus": d.get("vcpus", ""),
                "memory": d.get("memory", ""),
                "disk": d.get("disk", ""),
            }
        }],
    }


def main() -> int:
    if not TOKEN:
        print("ERROR: DIGITALOCEAN_ACCESS_TOKEN env var is not set. "
              "Nothing written (no secrets created).", file=sys.stderr)
        return 1
    # Load existing state so the 7 AWS/Azure/Oracle/Alibaba entries are preserved.
    try:
        with open(STATE) as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {"version": 4, "terraform_version": "1.9.0", "serial": 1,
                 "lineage": "skydash-do-seeded", "outputs": {}, "resources": []}
    state.setdefault("resources", [])
    known = existing_droplet_ids(state)

    added = 0
    seen = set()
    url = f"{API}/droplets?per_page=200"
    while url:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
        except requests.RequestException as e:
            print(f"ERROR: network failure calling DO API: {e}", file=sys.stderr)
            return 1
        if resp.status_code == 401:
            print("ERROR: DO API rejected the token (401 Unauthorized).", file=sys.stderr)
            return 1
        resp.raise_for_status()
        body = resp.json()
        for d in body.get("droplets", []):
            did = str(d.get("id") or "")
            if did in known or did in seen:
                continue
            seen.add(did)
            state["resources"].append(droplet_to_resource(d))
            added += 1
            print(f"  added: {d.get('name')} (id={did}, size={_size_slug(d)}, "
                  f"region={_region_slug(d)}, status={d.get('status')}, ip={_ips(d)[0]})")
        nxt = (body.get("links") or {}).get("pages", {}).get("next")
        url = nxt

    state["serial"] = int(state.get("serial", 0)) + 1
    with open(STATE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"\nDone. Added {added} DigitalOcean droplet(s) to {STATE} "
          f"({len(known)} already known). Existing entries preserved.")
    print("Restart the dashboard:  sudo systemctl restart skydash")
    return 0


if __name__ == "__main__":
    sys.exit(main())
