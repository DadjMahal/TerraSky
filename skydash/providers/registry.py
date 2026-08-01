"""Provider registry mapping normalized provider keys to provider instances.

The rest of the application depends only on this registry, never on concrete
provider classes, so new providers are added here alone.
"""
from __future__ import annotations

from providers.alibaba import AlibabaProvider
from providers.aws import AwsProvider
from providers.azure import AzureProvider
from providers.oracle import OracleProvider

_REGISTRY = {
    "aws": AwsProvider(),
    "azure": AzureProvider(),
    "oracle": OracleProvider(),
    "alibaba": AlibabaProvider(),
}


def get_provider(key: str):
    """Return the provider instance for `key`, or None if unknown."""
    return _REGISTRY.get(key)


def all_providers():
    """Return all registered provider instances."""
    return list(_REGISTRY.values())
