# Provider Framework — Design

> Extends the existing `providers/base.py` + `registry.py` into a full plugin
> architecture per §7, §10, §72-73.

## Current State

**File:** `skydash/providers/base.py` — `CloudProvider` ABC (lines 15-130)

```python
class CloudProvider(abc.ABC):
    key: str = ""
    @abstractmethod
    def available(self) -> bool: ...        # §2.2 capability check
    def get_status(self, instance) -> (status, error, public_ip, private_ip): ...
    @abstractmethod
    def start_instance(self, instance) -> (bool, msg): ...
    @abstractmethod
    def stop_instance(self, instance) -> (bool, msg): ...
    def get_logs(self, instance, log_type) -> list[str]: ...  # default impl
    def get_instance_details(self, instance) -> Instance: ...
```

**Registry:** `providers/registry.py:14-20` registers 5 providers:
`aws → AwsProvider`, `azure → AzureProvider`, `oracle → OracleProvider`,
`alibaba → AlibabaProvider`, `digitalocean → DigitalOceanProvider`

**Provider discovery (routing):** `app.py:18` `get_provider(key)` → `registry.py:23`

## Gap vs. Spec

| § | Requirement | Current | Gap |
|---|---|---|---|
| §7 | Provider Framework (adapter pattern) | ABC + registry | No formal framework, no lifecycle hooks |
| §8 | Provider Discovery (auto-discover resources) | tfstate reading only | No live auto-discovery |
| §9 | Custom Provider Framework | hermes_agent.py (SSH) | Not a registered provider |
| §10 | Provider Adapter SDK | None | No SDK for building new providers |
| §72 | Plugin Architecture | None | No plugin loading mechanism |
| §73 | Plugin Security | None | No least-privilege plugin model |

## Proposed Provider Adapter SDK (§10)

### Interface (extends `base.py`)

```python
class CloudProvider(abc.ABC):
    key: str = ""            # normalized provider key
    label: str = ""          # human-readable name

    @abc.abstractmethod
    def available(self) -> bool:
        """Return True if SDK + credentials present."""

    @abc.abstractmethod
    def get_capabilities(self) -> set[str]:
        """§2.2 — return supported operations:
        {create, destroy, start, stop, reboot, resize, snapshot,
         attach_volume, firewall, networking, logs, metrics, file_transfer,
         execute, service_restart, ...}
        """

    @abc.abstractmethod
    def get_status(self, instance) -> tuple[str, str, str, str]:
        """Return (normalized_status, error, public_ip, private_ip)."""

    @abc.abstractmethod
    def start_instance(self, instance) -> tuple[bool, str]: ...
    @abc.abstractmethod
    def stop_instance(self, instance) -> tuple[bool, str]: ...

    def reboot_instance(self, instance) -> tuple[bool, str]: ...
    def resize_instance(self, instance, new_size) -> tuple[bool, str]: ...
    def destroy_instance(self, instance) -> tuple[bool, str]: ...
    def create_instance(self, spec: dict) -> tuple[bool, str]: ...
    def attach_volume(self, instance, volume_size) -> tuple[bool, str]: ...

    def get_logs(self, instance, log_type) -> list[str]: ...
    def get_instance_details(self, instance) -> Instance: ...
    def list_resources(self) -> list[dict]: ...    # §8 discovery
    def sync(self) -> list[Instance]: ...          # §42 periodic sync
```

### Capability Discovery (§2.2, §101)

UI discovers actions dynamically:
```python
provider = get_provider(instance.provider)
caps = provider.get_capabilities()  # set of supported operations
# UI only renders buttons for operations in caps
```

### Provider Registry (extended)

```python
# providers/registry.py
_REGISTRY: dict[str, CloudProvider] = {}

def register(name: str, provider_cls):
    """Register a provider class (plugins call this at import)."""
    _REGISTRY[name] = provider_cls()

def get_provider(key: str) -> CloudProvider | None:
    return _REGISTRY.get(key)

def all_providers() -> list[CloudProvider]:
    return list(_REGISTRY.values())

def available_providers() -> list[CloudProvider]:
    """§83 — only providers with credentials present."""
    return [p for p in _REGISTRY.values() if p.available()]
```

### Lazy SDK Loading (already in place)

Each provider imports its SDK lazily inside methods (e.g., `aws.py:42` `import boto3`,
`oracle.py:60` `import oci`). This keeps memory low on the 1 GB host and prevents
crashes when an SDK or credential is missing.

### Credential Resolution

| Provider | Env Var Pattern | § Reference |
|---|---|---|
| AWS | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` | §100 |
| Azure | `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_TENANT_ID`, `ARM_SUBSCRIPTION_ID` | §100 |
| Oracle | `OCI_USER_OCID`, `OCI_TENANCY_OCID`, `OCI_FINGERPRINT`, `OCI_PRIVATE_KEY_PATH`, `OCI_REGION` | §100 |
| DigitalOcean | `DIGITALOCEAN_ACCESS_TOKEN` | §100 |
| Alibaba | `ALICLOUD_ACCESS_KEY`, `ALICLOUD_SECRET`, `ALICLOUD_REGION` | §100 |
| Custom SSH | `SSH_HOST`, `SSH_USER`, `SSH_KEY_PATH` | §9 |

All read from `terraform/.env` (git-ignored, §124) at startup.

### Plugin Loading (§72)

```python
# plugins/ directory, each plugin is a Python module
# plugin implements CloudProvider interface + declares permissions (§73)
def load_plugins():
    for path in discover_plugins("plugins/"):
        mod = importlib.import_module(path)
        mod.register(registry)  # §73: declares minimal permissions
```

### Existing Provider Implementations (all PARTIALLY IMPLEMENTED)

| Provider | File | Capabilities | Missing |
|---|---|---|---|
| AWS | `providers/aws.py` | status, start, stop, logs | create, destroy, resize, reboot, snapshot, capabilities, sync |
| Azure | `providers/azure.py` | status, start, stop, logs | same gaps |
| Oracle | `providers/oracle.py` | status(VNIC IPs), start, stop, logs | same gaps |
| Alibaba | `providers/alibaba.py` | status, start, stop, logs | same gaps |
| DigitalOcean | `providers/digitalocean.py` | status, start, stop, logs | same gaps |
| Custom SSH | `hermes_agent.py` | file_transfer, execute, service_management | not registered as provider |

### Custom SSH Provider (§9) — To Be Built

Wrap `hermes_agent.py` as a registered `CloudProvider` with capabilities:
`reboot`, `execute_command`, `upload_file`, `download_file`, `service_restart`.
