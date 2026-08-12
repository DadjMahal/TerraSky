"""Azure provider implementation using azure-identity and azure-mgmt-compute.

SDKs are imported lazily to keep memory low. Terraform does not persist Azure VM
power state, so it is read live from the VM instance view.
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

# Azure PowerState code -> normalized dashboard status.
_AZURE_POWER_MAP = {
    "running": STATUS_RUNNING,
    "starting": STATUS_STARTING,
    "stopped": STATUS_STOPPED,
    "stopping": STATUS_STOPPING,
    "deallocating": STATUS_STOPPING,
    "deallocated": STATUS_STOPPED,
}


class AzureProvider(CloudProvider):
    key = "azure"
    capabilities = ("read", "start", "stop", "reboot", "get_logs")

    # Cached clients to avoid repeated OAuth2 token acquisition
    _cached_client = None
    _cached_network_client = None
    _client_lock = None

    def __init__(self):
        super().__init__()
        self._client_lock = __import__('threading').Lock()

    def available(self) -> bool:
        return all(
            os.environ.get(k)
            for k in ("ARM_SUBSCRIPTION_ID", "ARM_CLIENT_ID", "ARM_CLIENT_SECRET", "ARM_TENANT_ID")
        )

    def _client(self):
        from azure.identity import ClientSecretCredential
        from azure.mgmt.compute import ComputeManagementClient

        if self._cached_client is not None:
            return self._cached_client
        with self._client_lock:
            if self._cached_client is not None:  # double-checked locking
                return self._cached_client
            cred = ClientSecretCredential(
                client_id=os.environ["ARM_CLIENT_ID"],
                client_secret=os.environ["ARM_CLIENT_SECRET"],
                tenant_id=os.environ["ARM_TENANT_ID"],
            )
            self._cached_client = ComputeManagementClient(cred, os.environ["ARM_SUBSCRIPTION_ID"])
            return self._cached_client

    def _network_client(self):
        """Create a Network Management Client for live IP lookups.

        Returns None if azure-mgmt-network is not installed.
        """
        try:
            from azure.identity import ClientSecretCredential
            from azure.mgmt.network import NetworkManagementClient

            if self._cached_network_client is not None:
                return self._cached_network_client
            with self._client_lock:
                if self._cached_network_client is not None:
                    return self._cached_network_client
                cred = ClientSecretCredential(
                    client_id=os.environ["ARM_CLIENT_ID"],
                    client_secret=os.environ["ARM_CLIENT_SECRET"],
                    tenant_id=os.environ["ARM_TENANT_ID"],
                )
                self._cached_network_client = NetworkManagementClient(cred, os.environ["ARM_SUBSCRIPTION_ID"])
                return self._cached_network_client
        except ImportError:
            return None

    def _get_live_ips(self, instance: Instance) -> tuple[str, str]:
        """Fetch live public/private IPs from Azure network interfaces.

        Deprecated: IP fetching is now inline in get_status() for efficiency.
        Kept as a fallback for other callers. Returns ("", "") on any error.
        """
        try:
            rg, vm = self._rg_vm(instance)
            if not rg or not vm:
                return "", ""
            vm_data = self._client().virtual_machines.get(rg, vm)
            net_client = self._network_client()
            if not net_client:
                return "", ""
            public_ip = ""
            private_ip = ""
            for ni_ref in (vm_data.network_profile.network_interfaces or []):
                ni_name = ni_ref.id.split("/")[-1]
                ni = net_client.network_interfaces.get(rg, ni_name)
                for ip_config in (ni.ip_configurations or []):
                    if ip_config.private_ip_address:
                        private_ip = ip_config.private_ip_address
                    if ip_config.public_ip_address and ip_config.public_ip_address.id:
                        pip_name = ip_config.public_ip_address.id.split("/")[-1]
                        pip = net_client.public_ip_addresses.get(rg, pip_name)
                        if pip.ip_address:
                            public_ip = pip.ip_address
            return public_ip, private_ip
        except Exception:
            return "", ""

    def _rg_vm(self, instance: Instance):
        # Resource group and VM name are stored in state and carried via extra.
        rg = instance.extra.get("resource_group_name")
        vm = instance.extra.get("vm_name") or instance.display_name
        return rg, vm

    def get_status(self, instance: Instance) -> tuple[str, str, str, str]:
        """Fetch live power state and IP addresses from Azure.

        ALWAYS prefers live data from the Azure API over stale Terraform state
        values. Uses a single `virtual_machines.get(expand='instanceView')` call
        to get both the power state and network interface refs in one request.
        Skips IP fetching for stopped/deallocated VMs (no public IP anyway).
        """
        try:
            rg, vm = self._rg_vm(instance)
            if not rg or not vm:
                return STATUS_UNKNOWN, "Azure: missing resource group / VM name", instance.public_ip, instance.private_ip
            # Single API call: get VM model + instance view (power state) together
            vm_data = self._client().virtual_machines.get(rg, vm, expand="instanceView")
            status = STATUS_UNKNOWN
            # Power state is in the instance view (embedded in the get response)
            for s in (vm_data.instance_view.statuses or []):
                code = s.code or ""
                if code.startswith("PowerState/"):
                    status = _AZURE_POWER_MAP.get(code.split("/", 1)[1].lower(), STATUS_UNKNOWN)
            # Skip IP fetching for stopped/deallocated VMs — they have no public IP
            if status in (STATUS_STOPPED, STATUS_STOPPING):
                return status, "", instance.public_ip, instance.private_ip
            # Fetch live IPs from network interfaces (only for running VMs)
            live_public, live_private = "", ""
            net_client = self._network_client()
            if net_client and vm_data.network_profile and vm_data.network_profile.network_interfaces:
                for ni_ref in vm_data.network_profile.network_interfaces:
                    ni_name = ni_ref.id.split("/")[-1]
                    try:
                        ni = net_client.network_interfaces.get(rg, ni_name)
                        for ip_config in (ni.ip_configurations or []):
                            if ip_config.private_ip_address:
                                live_private = ip_config.private_ip_address
                            if ip_config.public_ip_address and ip_config.public_ip_address.id:
                                pip_name = ip_config.public_ip_address.id.split("/")[-1]
                                pip = net_client.public_ip_addresses.get(rg, pip_name)
                                if pip.ip_address:
                                    live_public = pip.ip_address
                    except Exception:
                        pass  # skip this NI, try the next
            public_ip = live_public or instance.public_ip
            private_ip = live_private or instance.private_ip
            return status, "", public_ip, private_ip
        except Exception as e:
            return STATUS_ERROR, f"Azure: {e}", instance.public_ip, instance.private_ip

    def start_instance(self, instance: Instance) -> tuple[bool, str]:
        try:
            rg, vm = self._rg_vm(instance)
            # begin_start submits the operation; we do not block on the LRO so the
            # UI can reflect a transitional STATUS_STARTING state immediately.
            self._client().virtual_machines.begin_start(rg, vm)
            return True, f"Start request sent to {instance.name}"
        except Exception as e:
            return False, f"Azure start error: {e}"

    def stop_instance(self, instance: Instance) -> tuple[bool, str]:
        try:
            rg, vm = self._rg_vm(instance)
            # Deallocate stops the VM and stops compute billing.
            self._client().virtual_machines.begin_deallocate(rg, vm)
            return True, f"Stop (deallocate) request sent to {instance.name}"
        except Exception as e:
            return False, f"Azure stop error: {e}"
