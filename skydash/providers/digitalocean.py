"""DigitalOcean provider implementation using the DigitalOcean API v2.

The SDK is imported lazily (via ``requests``, a transitive dependency of boto3,
so no extra package is required), keeping memory low.  The Droplet *id* for each
managed instance comes from the Terraform state (``digitalocean_droplet``
resource), exactly like the AWS instance IDs come from ``aws_instance`` state.

Credentials: a DigitalOcean API token with read/write scope on Droplets must be
available via the ``DIGITALOCEAN_ACCESS_TOKEN`` environment variable (set in
``terraform/.env``).  ``available()`` returns False until it is present, so the
provider degrades gracefully (status -> error) without crashing the dashboard.
"""
from __future__ import annotations

import os

from models import (
    Instance,
    STATUS_ERROR,
    STATUS_RUNNING,
    STATUS_STARTING,
    STATUS_STOPPED,
    STATUS_STOPPING,
    STATUS_UNKNOWN,
)
from providers.base import CloudProvider

_API_BASE = "https://api.digitalocean.com/v2"
_DROPLET_STATE_MAP = {
    "active": STATUS_RUNNING,
    "off": STATUS_STOPPED,
    "new": STATUS_STARTING,
    "deleting": STATUS_STOPPING,
    "resizing": STATUS_STARTING,
    "migrating": STATUS_STARTING,
    "rebooting": STATUS_STARTING,
}


class DigitalOceanProvider(CloudProvider):
    key = "digitalocean"
    capabilities = ("read", "start", "stop", "reboot", "get_logs", "get_security_groups")

    def available(self) -> bool:
        # A personal access token is required to call the DO API at all.
        return bool(os.environ.get("DIGITALOCEAN_ACCESS_TOKEN"))

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {os.environ['DIGITALOCEAN_ACCESS_TOKEN']}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.digitalocean.v2+json",
        }

    def _request(self, method: str, path: str, **kwargs):
        import requests  # lazy: only loaded when a DO API call is actually made
        kwargs.setdefault("timeout", 10)
        return requests.request(method, _API_BASE + path, headers=self._headers(), **kwargs)

    def get_status(self, instance: Instance) -> tuple[str, str, str, str]:
        """Fetch live power state + IPs for a Droplet by id (DO API v2)."""
        if not self.available():
            return (STATUS_ERROR,
                    "DigitalOcean: DIGITALOCEAN_ACCESS_TOKEN not set",
                    instance.public_ip, instance.private_ip)
        try:
            resp = self._request("GET", f"/droplets/{instance.instance_id}")
            if resp.status_code == 404:
                return (STATUS_ERROR,
                        f"DigitalOcean: droplet {instance.instance_id} not found (404)",
                        instance.public_ip, instance.private_ip)
            resp.raise_for_status()
            droplet = resp.json().get("droplet", {})
            status = _DROPLET_STATE_MAP.get(droplet.get("status", ""), STATUS_UNKNOWN)
            # DO returns v4 addresses split into public/private under networks.
            v4 = ((droplet.get("networks") or {}).get("v4") or [])
            live_public = next((n.get("ip_address") for n in v4
                                if n.get("type") == "public" and n.get("ip_address")), "")
            live_private = next((n.get("ip_address") for n in v4
                                 if n.get("type") == "private" and n.get("ip_address")), "")
            return status, "", live_public or instance.public_ip, live_private or instance.private_ip
        except Exception as e:  # surface any failure to the UI as a status
            return STATUS_ERROR, f"DigitalOcean: {e}", instance.public_ip, instance.private_ip

    def start_instance(self, instance: Instance) -> tuple[bool, str]:
        try:
            if not self.available():
                return False, "DigitalOcean: DIGITALOCEAN_ACCESS_TOKEN not set"
            resp = self._request("POST", f"/droplets/{instance.instance_id}/actions",
                                 json={"type": "start"})
            if resp.status_code in (200, 201, 202, 204):
                return True, f"Start request sent to {instance.name}"
            return False, f"DigitalOcean start error: HTTP {resp.status_code} {resp.text[:200]}"
        except Exception as e:
            return False, f"DigitalOcean start error: {e}"

    def stop_instance(self, instance: Instance) -> tuple[bool, str]:
        # DO has no bare "stop" action; "shutdown" is the graceful ACPI shutdown,
        # matching the dashboard's Stop button semantics.
        try:
            if not self.available():
                return False, "DigitalOcean: DIGITALOCEAN_ACCESS_TOKEN not set"
            resp = self._request("POST", f"/droplets/{instance.instance_id}/actions",
                                 json={"type": "shutdown"})
            if resp.status_code in (200, 201, 202, 204):
                return True, f"Stop request sent to {instance.name}"
            return False, f"DigitalOcean stop error: HTTP {resp.status_code} {resp.text[:200]}"
        except Exception as e:
            return False, f"DigitalOcean stop error: {e}"

    def get_instance_details(self, instance: Instance) -> Instance:
        """Enrich with live status (base impl refreshes live status + can_manage)."""
        return super().get_instance_details(instance)

    def get_security_groups(self, instance: Instance) -> list:
        """Return DigitalOcean Cloud Firewalls applied to the Droplet.

        DO firewalls are referenced by Droplet. We list all firewalls and pick
        the ones referencing this Droplet id, then parse their
        ``inbound_rules`` and ``outbound_rules``.
        """
        from providers.security_groups import make_group, make_rule

        if not self.available():
            return []
        try:
            resp = self._request("GET", "/firewalls")
            resp.raise_for_status()
            firewalls = (resp.json() or {}).get("firewalls", []) or []
        except Exception as e:
            instance.error = "DigitalOcean firewall lookup error: " + str(e)
            return []

        droplet_id = instance.instance_id
        droplet_name = instance.display_name
        groups: list = []
        for fw in firewalls:
            applied = fw.get("droplets", []) or []
            attached = any(
                str(d.get("id") or d.get("name", "")) == str(droplet_id)
                or str(d.get("name", "")) == str(droplet_name)
                for d in applied
            )
            if not attached:
                continue
            inbound, outbound = [], []
            for r in fw.get("inbound_rules", []) or []:
                proto = r.get("protocol", "all")
                pf = r.get("ports")
                port_from, port_to = None, None
                if isinstance(pf, str) and "-" in pf:
                    a, b = pf.split("-", 1)
                    port_from, port_to = a.strip(), b.strip()
                elif isinstance(pf, str) and pf.isdigit():
                    port_from = port_to = pf
                src = r.get("source", {})
                source = src.get("address", src.get("security_group_id", ""))
                inbound.append(make_rule(proto, port_from, port_to,
                                         source or "0.0.0.0/0", "inbound",
                                         "allow", r.get("description", "") or ""))
            for r in fw.get("outbound_rules", []) or []:
                proto = r.get("protocol", "all")
                pf = r.get("ports")
                port_from, port_to = None, None
                if isinstance(pf, str) and "-" in pf:
                    a, b = pf.split("-", 1)
                    port_from, port_to = a.strip(), b.strip()
                elif isinstance(pf, str) and pf.isdigit():
                    port_from = port_to = pf
                dest = r.get("destination", {})
                dest_addr = dest.get("address", dest.get("security_group_id", ""))
                outbound.append(make_rule(proto, port_from, port_to,
                                          dest_addr or "0.0.0.0/0", "outbound",
                                          "allow", r.get("description", "") or ""))
            groups.append(make_group(
                str(fw.get("id", "")), fw.get("name", ""),
                "DO Cloud Firewall", self.key, inbound, outbound,
            ))
        return groups
