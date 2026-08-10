"""Alibaba Cloud provider implementation using the ECS SDK.

The SDK is imported lazily. Instance status is read via DescribeInstances;
start/stop use StartInstance / StopInstance.
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

# Alibaba ECS status -> normalized dashboard status.
_ALI_STATE_MAP = {
    "running": STATUS_RUNNING,
    "starting": STATUS_STARTING,
    "stopping": STATUS_STOPPING,
    "stopped": STATUS_STOPPED,
}


class AlibabaProvider(CloudProvider):
    key = "alibaba"
    capabilities = ("read", "start", "stop", "get_logs")
    _cached_client = None
    _client_lock = None

    def __init__(self):
        super().__init__()
        self._client_lock = __import__('threading').Lock()

    def available(self) -> bool:
        return bool(os.environ.get("ALICLOUD_ACCESS_KEY") and os.environ.get("ALICLOUD_SECRET_KEY"))

    def _client(self):
        from alibabacloud_ecs20140526.client import Client as EcsClient
        from alibabacloud_tea_openapi.models import Config

        if self._cached_client is not None:
            return self._cached_client
        with self._client_lock:
            if self._cached_client is not None:
                return self._cached_client
            config = Config(
                access_key_id=os.environ["ALICLOUD_ACCESS_KEY"],
                access_key_secret=os.environ["ALICLOUD_SECRET_KEY"],
                region_id=os.environ.get("ALICLOUD_REGION"),
            )
            self._cached_client = EcsClient(config)
            return self._cached_client

    def get_status(self, instance: Instance) -> tuple[str, str, str, str]:
        try:
            from alibabacloud_ecs20140526 import models as ecs_models

            # instance_ids expects a JSON-encoded array string.
            req = ecs_models.DescribeInstancesRequest(
                instance_ids=f'["{instance.instance_id}"]',
                region_id=os.environ.get("ALICLOUD_REGION"),
            )
            resp = self._client().describe_instances(req)
            insts = resp.body.instances.instance if (resp.body and resp.body.instances) else []
            if not insts:
                return STATUS_UNKNOWN, "", instance.public_ip, instance.private_ip
            
            ali_inst = insts[0]
            state = ali_inst.status if hasattr(ali_inst, 'status') else "unknown"
            
            # Get IPs from the response — ALWAYS prefer live data over TF state
            public_ip = ""
            private_ip = ""
            # Private IP (inner_ip)
            if hasattr(ali_inst, 'inner_ip') and ali_inst.inner_ip:
                private_ip = ali_inst.inner_ip
            # Public IP
            if hasattr(ali_inst, 'public_ip') and ali_inst.public_ip:
                public_ip = ali_inst.public_ip
            # EIP (Elastic IP) — stored separately and can change
            if not public_ip and hasattr(ali_inst, 'eip_address') and ali_inst.eip_address:
                eip = ali_inst.eip_address
                if hasattr(eip, 'ip_address') and eip.ip_address:
                    public_ip = eip.ip_address
            # Fall back to TF state only if API returned nothing
            public_ip = public_ip or instance.public_ip
            private_ip = private_ip or instance.private_ip
            
            return _ALI_STATE_MAP.get(str(state).lower(), STATUS_UNKNOWN), "", public_ip, private_ip
        except Exception as e:
            return STATUS_ERROR, f"Alibaba: {e}", instance.public_ip, instance.private_ip

    def start_instance(self, instance: Instance) -> tuple[bool, str]:
        try:
            from alibabacloud_ecs20140526 import models as ecs_models

            self._client().start_instance(ecs_models.StartInstanceRequest(instance_id=instance.instance_id))
            return True, f"Start request sent to {instance.name}"
        except Exception as e:
            return False, f"Alibaba start error: {e}"

    def stop_instance(self, instance: Instance) -> tuple[bool, str]:
        try:
            from alibabacloud_ecs20140526 import models as ecs_models

            self._client().stop_instance(ecs_models.StopInstanceRequest(instance_id=instance.instance_id))
            return True, f"Stop request sent to {instance.name}"
        except Exception as e:
            return False, f"Alibaba stop error: {e}"
