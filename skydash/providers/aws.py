"""AWS provider implementation using boto3.

boto3 is imported lazily inside each method so the heavy SDK is only loaded when
AWS is actually used, keeping memory usage low on the 1 GB host. Credentials are
read automatically by boto3 from the AWS_* environment variables.
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

# EC2 state name -> normalized dashboard status.
_EC2_STATE_MAP = {
    "running": STATUS_RUNNING,
    "pending": STATUS_STARTING,
    "stopping": STATUS_STOPPING,
    "shutting-down": STATUS_STOPPING,
    "stopped": STATUS_STOPPED,
    "terminated": STATUS_STOPPED,
}


class AwsProvider(CloudProvider):
    key = "aws"
    capabilities = ("read", "start", "stop", "reboot", "get_logs")

    def available(self) -> bool:
        # boto3 reads credentials from the environment, so presence of the key
        # pair is enough to consider the provider manageable.
        return bool(os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"))

    def _client(self, instance: Instance):
        import boto3  # lazy import to limit memory

        region = instance.region or os.environ.get("AWS_DEFAULT_REGION")
        return boto3.client("ec2", region_name=region)

    def get_status(self, instance: Instance) -> tuple[str, str, str, str]:
        """Fetch live status and IP addresses from AWS EC2 API.

        ALWAYS prefers live data from the AWS API over stale Terraform state
        values. When an instance is stopped, AWS returns no public IP — in that
        case we fall back to the TF state value so the card still shows something.
        """
        try:
            resp = self._client(instance).describe_instances(InstanceIds=[instance.instance_id])
            state = "unknown"
            live_public_ip = ""
            live_private_ip = ""
            for r in resp.get("Reservations", []):
                for i in r.get("Instances", []):
                    state = i.get("State", {}).get("Name", "unknown")
                    # Always read live IPs directly from the instance response
                    live_private_ip = i.get("PrivateIpAddress") or live_private_ip
                    live_public_ip = i.get("PublicIpAddress") or live_public_ip
                    # Fallback: check network interface associations for public IP
                    if not live_public_ip:
                        for ni in i.get("NetworkInterfaces", []):
                            assoc = ni.get("Association")
                            if assoc and assoc.get("PublicIp"):
                                live_public_ip = assoc["PublicIp"]
                                break
            # Use live IPs; fall back to TF state only if API returned nothing
            public_ip = live_public_ip or instance.public_ip
            private_ip = live_private_ip or instance.private_ip
            return _EC2_STATE_MAP.get(state, STATUS_UNKNOWN), "", public_ip, private_ip
        except Exception as e:  # surface any failure to the UI as a status
            return STATUS_ERROR, f"AWS: {e}", instance.public_ip, instance.private_ip

    def start_instance(self, instance: Instance) -> tuple[bool, str]:
        try:
            self._client(instance).start_instances(InstanceIds=[instance.instance_id])
            return True, f"Start request sent to {instance.name}"
        except Exception as e:
            return False, f"AWS start error: {e}"

    def stop_instance(self, instance: Instance) -> tuple[bool, str]:
        try:
            self._client(instance).stop_instances(InstanceIds=[instance.instance_id])
            return True, f"Stop request sent to {instance.name}"
        except Exception as e:
            return False, f"AWS stop error: {e}"
