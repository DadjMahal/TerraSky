"""Tests for scheduler — stdlib-only in-process job scheduler (§91).

Pure stdlib: time.monotonic / time.sleep are mocked so ticks are
 deterministic and no real 1s sleeps ever happen; threading is exercised
 without long waits (daemon threads are stopped right after starting).
"""
from __future__ import annotations

import os
import sys
import threading
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scheduler


# --------------------------------------------------------------------------- #
# Job dataclass                                                               #
# --------------------------------------------------------------------------- #
def test_job_defaults():
    def fn():
        return 42

    job = scheduler.Job(name="j", fn=fn, interval_seconds=60)
    assert job.name == "j"
    assert job.fn is fn
    assert job.interval_seconds == 60
    assert job.last_run is None
    # a real lock-like object is allocated per job (acquire/release)
    assert callable(getattr(job._lock, "acquire"))
    assert callable(getattr(job._lock, "release"))


def test_job_lock_is_per_instance():
    job_a = scheduler.Job(name="a", fn=lambda: None, interval_seconds=1)
    job_b = scheduler.Job(name="b", fn=lambda: None, interval_seconds=1)
    assert job_a._lock is not job_b._lock


# --------------------------------------------------------------------------- #
# register                                                                    #
# --------------------------------------------------------------------------- #
def test_register_adds_job():
    s = scheduler.Scheduler()
    job = scheduler.Job(name="cleanup", fn=lambda: None, interval_seconds=5)
    s.register(job)
    assert s._jobs == [job]


def test_register_is_idempotent_by_name():
    s = scheduler.Scheduler()
    first = scheduler.Job(name="cleanup", fn=lambda: None, interval_seconds=5)
    second = scheduler.Job(name="cleanup", fn=lambda: None, interval_seconds=10)
    s.register(first)
    s.register(second)
    assert s._jobs == [second]
    assert len(s._jobs) == 1


def test_register_keeps_distinct_names():
    s = scheduler.Scheduler()
    a = scheduler.Job(name="a", fn=lambda: None, interval_seconds=1)
    b = scheduler.Job(name="b", fn=lambda: None, interval_seconds=1)
    s.register(a)
    s.register(b)
    assert s._jobs == [a, b]


# --------------------------------------------------------------------------- #
# tick                                                                        #
# --------------------------------------------------------------------------- #
def test_tick_runs_new_job_immediately_and_records_last_run():
    s = scheduler.Scheduler()
    fn = mock.Mock()
    job = scheduler.Job(name="cold", fn=fn, interval_seconds=60)
    s.register(job)
    with mock.patch.object(scheduler.time, "monotonic", return_value=100.0):
        ran = s.tick()
    assert ran == ["cold"]
    fn.assert_called_once_with()
    assert job.last_run == 100.0


def test_tick_skips_job_that_is_not_due():
    s = scheduler.Scheduler()
    fn = mock.Mock()
    job = scheduler.Job(name="warm", fn=fn, interval_seconds=10, last_run=100.0)
    s.register(job)
    with mock.patch.object(scheduler.time, "monotonic", return_value=105.0):
        ran = s.tick()
    assert ran == []
    fn.assert_not_called()


def test_tick_runs_job_once_interval_elapsed():
    s = scheduler.Scheduler()
    fn = mock.Mock()
    job = scheduler.Job(name="due", fn=fn, interval_seconds=10, last_run=100.0)
    s.register(job)
    with mock.patch.object(scheduler.time, "monotonic", return_value=112.0):
        ran = s.tick()
    assert ran == ["due"]
    fn.assert_called_once_with()
    assert job.last_run == 112.0


def test_tick_interval_zero_runs_every_tick():
    s = scheduler.Scheduler()
    fn = mock.Mock()
    job = scheduler.Job(name="z", fn=fn, interval_seconds=0, last_run=100.0)
    s.register(job)
    with mock.patch.object(scheduler.time, "monotonic", return_value=100.0):
        ran = s.tick()
    assert ran == ["z"]
    fn.assert_called_once_with()


def test_tick_returns_all_due_jobs_in_order():
    s = scheduler.Scheduler()
    fn_a = mock.Mock()
    fn_b = mock.Mock()
    s.register(scheduler.Job(name="a", fn=fn_a, interval_seconds=5))
    s.register(scheduler.Job(name="b", fn=fn_b, interval_seconds=5))
    with mock.patch.object(scheduler.time, "monotonic", return_value=500.0):
        ran = s.tick()
    assert ran == ["a", "b"]


def test_tick_swallows_job_exception_and_still_returns_name():
    s = scheduler.Scheduler()
    def boom():
        raise RuntimeError("job failed")
    job = scheduler.Job(name="flaky", fn=boom, interval_seconds=1)
    s.register(job)
    with mock.patch.object(scheduler.time, "monotonic", return_value=1.0):
        ran = s.tick()  # must not raise
    assert ran == ["flaky"]
    assert job.last_run == 1.0


def test_tick_one_failing_job_does_not_block_others():
    s = scheduler.Scheduler()
    def boom():
        raise RuntimeError("boom")
    fn_ok = mock.Mock(return_value=None)
    s.register(scheduler.Job(name="bad", fn=boom, interval_seconds=1))
    s.register(scheduler.Job(name="good", fn=fn_ok, interval_seconds=1))
    with mock.patch.object(scheduler.time, "monotonic", return_value=1.0):
        ran = s.tick()
    assert ran == ["bad", "good"]
    fn_ok.assert_called_once_with()


def test_tick_recheck_skips_job_updated_by_prior_job():
    """If an earlier job in the same tick bumps another job's last_run, the
    second job — due at the snapshot — must be skipped by the per-lock
    re-check so it never runs twice in one tick."""
    s = scheduler.Scheduler()
    j2 = scheduler.Job(name="j2", fn=mock.Mock(), interval_seconds=10, last_run=0.0)

    def j1_fn():
        j2.last_run = 50.0  # simulate another concurrent tick already running j2

    j1 = scheduler.Job(name="j1", fn=j1_fn, interval_seconds=10, last_run=0.0)
    s.register(j1)
    s.register(j2)
    with mock.patch.object(scheduler.time, "monotonic", return_value=50.0):
        ran = s.tick()
    assert ran == ["j1"]
    # j2 was in the due snapshot but the re-check (50 - 50 < 10) skipped it
    j2.fn.assert_not_called()


def test_tick_job_never_runs_twice_in_one_tick():
    s = scheduler.Scheduler()
    calls = []
    def fn():
        calls.append(1)
        # a nested tick would try to re-run the same job but the per-job
        # lock (non-reentrant) prevents re-entry; we don't call it here,
        # just assert the outer tick runs fn exactly once.
    job = scheduler.Job(name="j", fn=fn, interval_seconds=1)
    s.register(job)
    with mock.patch.object(scheduler.time, "monotonic", return_value=1.0):
        s.tick()
    assert calls == [1]


# --------------------------------------------------------------------------- #
# start / stop / _loop                                                        #
# --------------------------------------------------------------------------- #
def test_start_spawns_daemon_thread():
    s = scheduler.Scheduler()
    try:
        s.start()
        assert s._thread is not None
        assert s._thread.is_alive()
        assert s._thread.name == "skydash-scheduler"
        assert s._thread.daemon is True
    finally:
        s.stop()
    assert not s._thread.is_alive()


def test_start_is_idempotent():
    s = scheduler.Scheduler()
    try:
        s.start()
        first = s._thread
        s.start()
        assert s._thread is first
    finally:
        s.stop()


def test_stop_clears_and_joins():
    s = scheduler.Scheduler()
    s.start()
    s._stop.clear()
    s.stop()
    assert s._stop.is_set()
    assert not s._thread.is_alive()


def test_stop_without_start_is_safe():
    s = scheduler.Scheduler()
    s.stop()  # no thread yet -> must not raise


def test_loop_ticks_until_stop():
    s = scheduler.Scheduler()
    with mock.patch.object(scheduler.time, "sleep",
                           side_effect=lambda secs: s._stop.set()) as sleep, \
            mock.patch.object(s, "tick", return_value=[]) as tick:
        s._loop()
    tick.assert_called_once()
    sleep.assert_called_once_with(1.0)

def test_loop_does_not_tick_when_stopped():
    s = scheduler.Scheduler()
    s._stop.set()
    with mock.patch.object(s, "tick") as tick:
        s._loop()
    tick.assert_not_called()


# --------------------------------------------------------------------------- #
# Module-level convenience API                                                #
# --------------------------------------------------------------------------- #
def test_default_scheduler_is_singleton():
    assert isinstance(scheduler._default, scheduler.Scheduler)


def test_register_module_level_returns_job_and_delegates():
    fake = mock.Mock()
    with mock.patch.object(scheduler, "_default", fake):
        job = scheduler.register("jobx", interval_seconds=5, fn=lambda: None)
    assert isinstance(job, scheduler.Job)
    assert job.name == "jobx"
    assert job.interval_seconds == 5
    fake.register.assert_called_once_with(job)


def test_start_module_level_delegates():
    fake = mock.Mock()
    with mock.patch.object(scheduler, "_default", fake):
        scheduler.start()
    fake.start.assert_called_once_with()


def test_stop_module_level_delegates():
    fake = mock.Mock()
    with mock.patch.object(scheduler, "_default", fake):
        scheduler.stop()
    fake.stop.assert_called_once_with()


def test_register_then_tick_end_to_end():
    """A module-level registered job actually fires via the default scheduler
    when the default is not running as a thread (tick is called directly)."""
    calls = []
    job = scheduler.register("e2e", interval_seconds=1, fn=lambda: calls.append(1))
    try:
        with mock.patch.object(scheduler.time, "monotonic", return_value=10.0):
            ran = scheduler._default.tick()
        assert ran == ["e2e"]
        assert calls == [1]
    finally:
        scheduler._default._jobs = [j for j in scheduler._default._jobs if j.name != "e2e"]


if __name__ == "__main__":
    import pytest as _pytest
    sys.exit(_pytest.main([__file__, "-v"]))
