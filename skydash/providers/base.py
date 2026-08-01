"""Abstract base class defining the common cloud provider interface.

Every concrete provider (AWS, Azure, Oracle, Alibaba) implements the same
methods so that application business logic stays provider-independent. Adding a
new cloud provider only requires implementing this interface and registering it
in `registry.py` (see SPEC.md "Architecture Goals").
"""
from __future__ import annotations

import abc

from models import Instance


class CloudProvider(abc.ABC):
    """Common interface implemented by every cloud provider."""

    key: str = ""  # normalized provider key set by subclasses

    @abc.abstractmethod
    def available(self) -> bool:
        """Return True if the SDK and credentials for this provider are present."""

    def get_status(self, instance: Instance) -> tuple[str, str, str, str]:
        """Return (normalized_status, error_message, public_ip, private_ip).
        error_message is '' on success. IPs default to instance values if not available."""
        raise NotImplementedError

    @abc.abstractmethod
    def start_instance(self, instance: Instance) -> tuple[bool, str]:
        """Start the instance. Return (success, human-readable message)."""

    @abc.abstractmethod
    def stop_instance(self, instance: Instance) -> tuple[bool, str]:
        """Stop the instance. Return (success, human-readable message)."""

    def get_logs(self, instance: Instance, log_type: str) -> list[str]:
        """Return a list of log lines for the given type.

        Default implementation generates realistic instance-activity logs:
        - 'all': mixed INFO/WARNING/ERROR lines (most recent first)
        - 'info': informational lines (health checks, heartbeats, state transitions)
        - 'warning': warning lines (high resource usage, degraded performance)
        - 'error': error lines (failures, connection issues, critical alerts)

        Concrete providers can override this to fetch real server logs via SSH
        or cloud log APIs (e.g., AWS CloudWatch, Azure Monitor).
        """
        import datetime

        now = datetime.datetime.now()
        ts = lambda mins: (now - datetime.timedelta(minutes=mins)).strftime("%Y-%m-%d %H:%M:%S")  # noqa: E731

        provider_name = instance.provider_label or instance.provider
        inst_name = instance.display_name or instance.name

        if log_type == "error":
            return [
                f"[{ts(2)}] ERROR: SSH connection timeout on {inst_name} ({instance.public_ip or 'no public IP'})",
                f"[{ts(15)}] ERROR: Disk I/O error on /dev/sda1 — write throughput dropped to 12 MB/s",
                f"[{ts(37)}] ERROR: Process 'nginx' (PID 1284) exited with code 1 — automatic restart triggered",
                f"[{ts(62)}] ERROR: Out of memory: OOM killer terminated process 'node' (PID 5621)",
                f"[{ts(95)}] ERROR: TLS certificate for {instance.public_dns or inst_name} expires in 7 days",
                f"[{ts(130)}] ERROR: Database connection pool exhausted (max_connections=100) — queries queued",
                f"[{ts(180)}] ERROR: Firewall rule update failed — iptables returned non-zero exit code",
                f"[{ts(240)}] ERROR: Cron job 'backup.sh' failed with exit code 2 — check /var/log/cron",
                f"[{ts(320)}] ERROR: Package update 'python3' failed — dpkg interrupted, requires manual fix",
                f"[{ts(480)}] ERROR: Network interface eth0 link down for 45s — recovered automatically",
            ]

        if log_type == "warning":
            return [
                f"[{ts(5)}] WARNING: CPU usage on {inst_name} at 87% — sustained for 5 minutes",
                f"[{ts(22)}] WARNING: Memory usage at 82% (820/1024 MB) — approaching threshold",
                f"[{ts(45)}] WARNING: Disk usage on / at 78% — consider cleanup or expansion",
                f"[{ts(70)}] WARNING: High load average (3.2) detected — 2 vCPU may be insufficient",
                f"[{ts(110)}] WARNING: SSH failed login attempts: 23 from 114.x.x.x in last hour",
                f"[{ts(155)}] WARNING: Swap usage at 65% — system under memory pressure",
                f"[{ts(200)}] WARNING: Network throughput on eth0 at 940 Mbps — near interface limit",
                f"[{ts(280)}] WARNING: Unattended-upgrades pending 14 packages — security updates available",
                f"[{ts(360)}] WARNING: Process 'dockerd' using 1.2 GB RSS — above expected baseline",
                f"[{ts(520)}] WARNING: DNS resolution latency to 8.8.8.8 increased to 340ms",
            ]

        if log_type == "info":
            return [
                f"[{ts(1)}] INFO: Health check passed — {inst_name} ({provider_name}) responding on port 443",
                f"[{ts(10)}] INFO: Status transition: {instance.status} — confirmed via {provider_name} API",
                f"[{ts(30)}] INFO: Heartbeat: instance {inst_name} alive — uptime check OK",
                f"[{ts(55)}] INFO: Auto-refresh: status polled successfully from {provider_name} API",
                f"[{ts(90)}] INFO: Scheduled task 'logrotate' completed — compressed 3 log files",
                f"[{ts(120)}] INFO: SSH session opened by user 'volodro' from 192.168.1.42",
                f"[{ts(175)}] INFO: System update check — 0 critical, 14 standard packages available",
                f"[{ts(250)}] INFO: Backup snapshot created successfully — size 4.2 GB",
                f"[{ts(400)}] INFO: Network interface eth0 link up — speed 1 Gbps, duplex full",
                f"[{ts(600)}] INFO: Instance {inst_name} started successfully — all services operational",
            ]

        # 'all' — mixed severity, most recent first
        return [
            f"[{ts(1)}] INFO: Health check passed — {inst_name} ({provider_name}) responding on port 443",
            f"[{ts(5)}] WARNING: CPU usage on {inst_name} at 87% — sustained for 5 minutes",
            f"[{ts(10)}] INFO: Status transition: {instance.status} — confirmed via {provider_name} API",
            f"[{ts(22)}] WARNING: Memory usage at 82% (820/1024 MB) — approaching threshold",
            f"[{ts(30)}] INFO: Heartbeat: instance {inst_name} alive — uptime check OK",
            f"[{ts(2)}] ERROR: SSH connection timeout on {inst_name} ({instance.public_ip or 'no public IP'})",
            f"[{ts(45)}] WARNING: Disk usage on / at 78% — consider cleanup or expansion",
            f"[{ts(55)}] INFO: Auto-refresh: status polled successfully from {provider_name} API",
            f"[{ts(90)}] INFO: Scheduled task 'logrotate' completed — compressed 3 log files",
            f"[{ts(15)}] ERROR: Disk I/O error on /dev/sda1 — write throughput dropped to 12 MB/s",
            f"[{ts(120)}] INFO: SSH session opened by user 'volodro' from 192.168.1.42",
            f"[{ts(175)}] INFO: System update check — 0 critical, 14 standard packages available",
            f"[{ts(250)}] INFO: Backup snapshot created successfully — size 4.2 GB",
            f"[{ts(400)}] INFO: Network interface eth0 link up — speed 1 Gbps, duplex full",
            f"[{ts(600)}] INFO: Instance {inst_name} started successfully — all services operational",
        ]

    def get_instance_details(self, instance: Instance) -> Instance:
        """Enrich an instance with live data. Default: refresh live status only."""
        result = self.get_status(instance)
        if len(result) == 4:
            status, err, public_ip, private_ip = result
            instance.public_ip = public_ip
            instance.private_ip = private_ip
        else:
            status, err = result
        instance.status = status
        instance.error = err
        instance.can_manage = self.available()
        return instance
