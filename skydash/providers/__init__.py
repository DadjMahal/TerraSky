"""Cloud provider package.

Each module implements the common :class:`providers.base.CloudProvider`
interface for one cloud. Importing this package does not import any cloud SDK;
SDKs are imported lazily by the provider methods to keep memory usage low on the
1 GB host.
"""
