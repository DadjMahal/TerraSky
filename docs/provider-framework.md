# SkyDash Provider Framework — Design

> **Created:** 2026-08-10 · Source: §2.1, §2.2, §7-10, §72-73 + actual `skydash/providers/`.
> Current state: `base.py` (ABC `CloudProvider`), `registry.py`, and 6 providers (AWS, Azure, OCI, Alibaba, DigitalOcean). Custom/SSH via `hermes_agent.py`.

## 1. Current Architecture (implemented)

```
registry.py (get_provider, all_providers)
   ├── base.CloudProvider (ABC)
   │      ├── available() -> bool
   │      ├── get_status(inst) -> (status, err, pub_ip, pri_ip)
   │      ├── start_instance / stop_instance
   │      ├── get_logs(inst, type)  (default = synthetic)
   │      └── get_instance_details(inst) (live refresh + can_manage)
   ├── aws.py      (boto3, lazy)
   ├── azure.py    (azure-mgmt, lazy, cached client)
   ├── oracle.py   (oci, lazy, cached config+client)
   ├── alibaba.py  (alibabacloud, lazy)
   └── digitalocean.py (requests, lazy)
```

**Good:** lazily-imported SDKs keep memory low; `available()` returns False gracefully; one provider failing does not block others (ThreadPoolExecutor in `/api/statuses`).

## 2. Gaps vs. Spec

| Spec | Gap | Fix |
|---|---|---|
| §2.2 Capability-Based | No capability declaration | Add `capabilities: list[str]` to each provider; UI discovers dynamically |
| §2.3 State model | No desired/actual split | Adopt `ResourceState` (desired vs provider vs monitored) |
| §8 Discovery | No auto-discovery | Add `discover()` listing accounts/regions/resources |
| §9 Custom/SSH | Not a formal provider | Package `hermes_agent.py` as a `CustomSSHProvider` |
| §10 SDK | No authoring SDK | Publish `CloudProvider` as importable interface + docs |
| §72-73 Plugins | No plugin packaging/security | Separate provider plugins with declared permissions |

## 3. Target Provider Interface (extension of current)

```python
class CloudProvider(abc.ABC):
    key: str
    capabilities: list[str] = []        # e.g. ["start","stop","reboot","snapshot"]
    # current methods...
    def discover(self, creds) -> list[dict]: ...   # §8
    def capabilities_ui(self) -> list[str]:        # §2.2
```

## 4. Generating a Custom SSH Provider (§9)

`CustomSSHProvider` wraps `hermes_agent.py`:
- capabilities: `["reboot","execute_command","upload_file","download_file","service_restart"]` (from spec example)
- profile from `~/.ssh/config` / stored keys
- `get_status` → SSH `uptime`/`systemctl is-system-running`

## 5. Adding a New Provider (checklist)

1. `providers/<name>.py` → subclass `CloudProvider` (lazy SDK import).
2. Register in `providers/registry.py`.
3. Add `RESOURCE_TYPE_PROVIDER` + `_map_<name>` in `state_reader.py`.
4. Add size specs to `instance_specs.py`.
5. Add `PROVIDER_ICONS`/`PROVIDER_LABELS` in `models.py`.
6. Add provider contract test (§116).
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

## 6. Iteration 2 — Delivered (capability-based architecture)

Implemented directly into the code (compile-verified; API not runtime-tested —
no Flask here):

| Item | § | What was added |
|---|---|---|
| Capability declaration | §2.2, §10 | `CloudProvider.capabilities` + `get_capabilities()` in `providers/base.py`; every provider declares its supported ops (awss/azure/do/oracle: read/start/stop/reboot/get_logs; alibaba: read/start/stop/get_logs; oracle: + get_instance_details) |
| Capability discovery API | §2.2, §83 | `GET /api/v1/providers` returns `{key, capabilities, available}` per provider via `providers/registry.py` |
| Custom SSH provider | §9, §18 | `providers/custom_ssh.py` — `CustomSSHProvider` reuses `hermes_agent` paramiko helpers; capabilities read/reboot/execute_command/service_restart/get_logs/disk/test_connection; power-off intentionally unsupported (no control plane); gracefully degrades when paramiko absent |
| Feature contracts | §16, §20-24 | `features/{files,processes,services,docker,k8s}.py` — documented agent-side command contracts + limits (`§79`), each marked `FEATURE_STATUS="scaffold"` and BLOCKED on a deployed agent |
| Graceful degradation | §83-84 | `v1_providers` never raises: a failing `available()` falls back to False; per-instance try/except already isolated in `/api/statuses` |

**Verification:** `python3 -m py_compile` over all touched modules + registry import
shows all 6 providers with correct capability lists and `available()=False` (no creds
in this environment — the expected degraded state). **Runtime API verification + deploy
pending.**
