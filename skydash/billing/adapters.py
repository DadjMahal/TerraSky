"""Billing import adapters (§56). Skeleton definitions.

Each adapter documents the *exact* provider API it would call. They raise
``NotImplementedError`` because live billing APIs require cloud credentials
that are not (and should not be) present in this repository. This keeps the
import surface honest: nothing fake is returned, ever.
"""
from __future__ import annotations

import abc
from typing import Any

from billing.model import CostRecord, Invoice


class BillingAdapter(abc.ABC):
    provider: str = ""

    @abc.abstractmethod
    def fetch_costs(self, period: str) -> list[CostRecord]:
        """Fetch normalized CostRecords for ``period`` (e.g. '2026-08')."""

    @abc.abstractmethod
    def fetch_invoices(self, period: str) -> list[Invoice]:
        """Fetch normalised Invoices for ``period``."""


class AwsBillingAdapter(BillingAdapter):
    provider = "aws"

    def fetch_costs(self, period: str) -> list[CostRecord]:
        raise NotImplementedError(
            "aws: would call AWS Cost Explorer get_cost_and_usage() with "
            "AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY; not executed here (no creds).")


class AzureBillingAdapter(BillingAdapter):
    provider = "azure"

    def fetch_costs(self, period: str) -> list[CostRecord]:
        raise NotImplementedError(
            "azure: would call Azure Cost Management Usages.generate() with "
            "ARM_TENANT_ID/ARM_CLIENT_ID/ARM_CLIENT_SECRET; not executed here.")


class OciBillingAdapter(BillingAdapter):
    provider = "oracle"

    def fetch_costs(self, period: str) -> list[CostRecord]:
        raise NotImplementedError(
            "oracle: would call OCI Usage API list_usage_summaries() with "
            "OCI_CONFIG / OCI_USER/OCI_TENANCY keys; not executed here.")


class DigitalOceanBillingAdapter(BillingAdapter):
    provider = "digitalocean"

    def fetch_costs(self, period: str) -> list[CostRecord]:
        raise NotImplementedError(
            "digitalocean: would call DO Billing /v2/customers/my/balances + "
            "invoices with DIGITALOCEAN_ACCESS_TOKEN; not executed here.")


class AlibabaBillingAdapter(BillingAdapter):
    provider = "alibaba"

    def fetch_costs(self, period: str) -> list[CostRecord]:
        raise NotImplementedError(
            "alibaba: would call Alibaba BSS QueryAccountBill with "
            "ALICLOUD_ACCESS_KEY_ID/ALICLOUD_ACCESS_KEY_SECRET; not executed here.")


def all_adapters() -> dict[str, BillingAdapter]:
    return {a.provider: a for a in (AwsBillingAdapter(), AzureBillingAdapter(), OciBillingAdapter(),
                                    DigitalOceanBillingAdapter(), AlibabaBillingAdapter())}
