"""Minimal, stdlib-only job scheduler (§91 — Scheduler).

Deliberately no external deps (no APScheduler/Celery/Redis): a daemon thread
ticks a 1-second loop and runs due jobs under a lock. This covers periodic
maintenance jobs (status-cache refresh, drift sweep, retention) without
requiring queue infrastructure. A real distributed queue (Redis/RQ or Celery)
is a production-hardening item (Iter 10) — this module is the in-process
fallback and is trivially unit-testable.

Usage::

    from scheduler import register, start, stop
    register("refresh-status-cache", interval_seconds=60, fn=lambda: cache.clear())
    start()   # daemon thread, stops with the interpreter
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from typing import Any, Callable


@dataclass
class Job:
    name: str
    fn: Callable[[], Any]
    interval_seconds: float
    last_run: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


class Scheduler:
    """Tick a 1s loop and run jobs whose interval has elapsed."""

    def __init__(self) -> None:
        self._jobs: list[Job] = []
        self._jobs_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def register(self, job: Job) -> None:
        with self._jobs_lock:
            self._jobs = [j for j in self._jobs if j.name != job.name]  # idempotent
            self._jobs.append(job)

    def tick(self) -> list[str]:
        """Run all due jobs; returns the names executed (testable without threads)."""
        now = time.monotonic()
        ran: list[str] = []
        with self._jobs_lock:
            due = [j for j in self._jobs if j.last_run is None or (now - j.last_run) >= j.interval_seconds]
        for job in due:
            with job._lock:  # never run the same job twice concurrently
                if job.last_run is not None and (now - job.last_run) < job.interval_seconds:
                    continue  # another tick already ran it
                try:
                    job.fn()
                except Exception:  # noqa: BLE001 - scheduler must never die
                    pass
                job.last_run = now
                ran.append(job.name)
        return ran

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="skydash-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.tick()
            time.sleep(1.0)


# Module-level default scheduler + convenience API
_default = Scheduler()


def register(name: str, interval_seconds: float, fn: Callable[[], Any]) -> Job:
    job = Job(name=name, fn=fn, interval_seconds=interval_seconds)
    _default.register(job)
    return job


def start() -> None:
    _default.start()


def stop() -> None:
    _default.stop()
