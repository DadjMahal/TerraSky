"""Oracle Cloud provider implementation using the OCI Python SDK.

The OCI SDK has no env-based config loader, so a config dict is built from the
OCI_* environment variables and validated. The SDK is imported lazily.
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

# OCI lifecycle state -> normalized dashboard status.
_OCI_STATE_MAP = {
    "RUNNING": STATUS_RUNNING,
    "STARTING": STATUS_STARTING,
    "STOPPING": STATUS_STOPPING,
    "STOPPED": STATUS_STOPPED,
    "PROVISIONING": STATUS_STARTING,
    "TERMINATED": STATUS_STOPPED,
    "TERMINATING": STATUS_STOPPING,
}


class OracleProvider(CloudProvider):
    key = "oracle"
    _cached_client = None
    _cached_network_client = None
    _client_lock = None

    def __init__(self):
        super().__init__()
        self._client_lock = __import__('threading').Lock()

    def available(self) -> bool:
        return all(
            os.environ.get(k)
            for k in ("OCI_USER_OCID", "OCI_TENANCY_OCID", "OCI_FINGERPRINT", "OCI_PRIVATE_KEY_PATH", "OCI_REGION")
        )

    def _config(self) -> dict:
        import oci

        config = {
            "user": os.environ["OCI_USER_OCID"],
            "tenancy": os.environ["OCI_TENANCY_OCID"],
            "fingerprint": os.environ["OCI_FINGERPRINT"],
            "key_file": os.environ["OCI_PRIVATE_KEY_PATH"],
            "region": os.environ["OCI_REGION"],
        }
        oci.config.validate_config(config)
        return config

    def _client(self):
        import oci

        if self._cached_client is not None:
            return self._cached_client
        with self._client_lock:
            if self._cached_client is not None:
                return self._cached_client
            self._cached_client = oci.core.ComputeClient(self._config())
            return self._cached_client

    def _network_client(self):
        import oci

        if self._cached_network_client is not None:
            return self._cached_network_client
        with self._client_lock:
            if self._cached_network_client is not None:
                return self._cached_network_client
            self._cached_network_client = oci.core.VirtualNetworkClient(self._config())
            return self._cached_network_client

    def _get_live_ips(self, instance: Instance) -> tuple[str, str]:
        """Fetch live public/private IPs from Oracle Cloud VNICs.

        OCI does not put IPs on the instance object — they're on VNIC attachments.
        We list VNIC attachments for the instance, then get the VNIC details.
        Returns ("", "") on any error (caller falls back to TF state values).
        """
        try:
            import oci

            compute = self._client()
            net = self._network_client()
            # List VNIC attachments for this instance
            attachments = compute.list_vnic_attachments(
                compartment_id=(
                    self._config()["tenancy"]
                    if not instance.extra.get("compartment_id")
                    else instance.extra["compartment_id"]
                ),
                instance_id=instance.instance_id,
            ).data
            public_ip = ""
            private_ip = ""
            for att in attachments:
                if not att.vnic_id:
                    continue
                vnic = net.get_vnic(att.vnic_id).data
                if vnic.private_ip:
                    private_ip = vnic.private_ip
                # Public IP may be on the VNIC directly
                if hasattr(vnic, "public_ip") and vnic.public_ip:
                    public_ip = vnic.public_ip
            return public_ip, private_ip
        except Exception:
            return "", ""

    def get_status(self, instance: Instance) -> tuple[str, str, str, str]:
        """Fetch live status and IP addresses from Oracle Cloud.

        ALWAYS prefers live data from the OCI API over stale Terraform state
        values. IPs are fetched from VNIC attachments (instance object has none).
        """
        try:
            resp = self._client().get_instance(instance.instance_id)
            data = resp.data
            state = data.lifecycle_state
            # Fetch live IPs from VNIC attachments
            live_public, live_private = self._get_live_ips(instance)
            public_ip = live_public or instance.public_ip
            private_ip = live_private or instance.private_ip
            return _OCI_STATE_MAP.get(state, STATUS_UNKNOWN), "", public_ip, private_ip
        except Exception as e:
            return STATUS_ERROR, f"Oracle: {e}", instance.public_ip, instance.private_ip

    def start_instance(self, instance: Instance) -> tuple[bool, str]:
        try:
            self._client().instance_action(instance.instance_id, action="START")
            return True, f"Start request sent to {instance.name}"
        except Exception as e:
            return False, f"Oracle start error: {e}"

    def stop_instance(self, instance: Instance) -> tuple[bool, str]:
        try:
            # SOFTSTOP lets the OS shut down gracefully before powering off.
            self._client().instance_action(instance.instance_id, action="SOFTSTOP")
            return True, f"Stop request sent to {instance.name}"
        except Exception as e:
            return False, f"Oracle stop error: {e}"
