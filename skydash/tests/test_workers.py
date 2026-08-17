"""Tests for workers — ephemeral worker + command-execution security (§74-75).

run_isolated() is verified against a mocked subprocess.run() so no real shell
commands or external processes are ever spawned by the tests. The approval
gate, command allowlist, output cap and error mapping are exercised as pure
stdlib logic.
"""
from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import workers


# --------------------------------------------------------------------------- #
# SAFE_COMMANDS constant                                                       #
# --------------------------------------------------------------------------- #
def test_safe_commands_constant():
    assert isinstance(workers.SAFE_COMMANDS, tuple)
    assert "ls" in workers.SAFE_COMMANDS
    assert "df" in workers.SAFE_COMMANDS
    assert "uptime" in workers.SAFE_COMMANDS


# --------------------------------------------------------------------------- #
# Approval gate                                                                #
# --------------------------------------------------------------------------- #
def test_require_approval_short_circuits_before_subprocess():
    with mock.patch("workers.subprocess.run") as run:
        result = workers.run_isolated("systemctl stop nginx", require_approval=True)
    assert result["ok"] is False
    assert result["code"] == "NEEDS_APPROVAL"
    assert "approval" in result["error"]
    assert "elapsed" in result
    run.assert_not_called()


def test_require_approval_false_proceeds_to_execution():
    # Just prove the gate is skipped: execution is attempted.
    with mock.patch("workers.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=0, stdout="ok\n", stderr="")
        result = workers.run_isolated("uptime", require_approval=False)
    assert result["ok"] is True
    run.assert_called_once()


# --------------------------------------------------------------------------- #
# Command allowlist                                                            #
# --------------------------------------------------------------------------- #
def test_command_not_in_allowlist_is_denied():
    with mock.patch("workers.subprocess.run") as run:
        result = workers.run_isolated("curl -s http://evil.example")
    assert result["ok"] is False
    assert result["code"] == "NOT_ALLOWED"
    assert "not in allowlist" in result["error"]
    assert "curl" in result["error"]
    run.assert_not_called()


def test_empty_allowlist_disables_check():
    """An empty allowlist is falsy, so the head-prefix guard is skipped entirely."""
    with mock.patch("workers.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
        result = workers.run_isolated("uptime", allowlist=())
    assert result["code"] == "OK"
    assert result["ok"] is True
    run.assert_called_once()


def test_allowlist_prefix_matching():
    """A command is accepted when its head starts with an allowlisted command."""
    with mock.patch("workers.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
        result = workers.run_isolated("ls -la /opt", allowlist=("ls",))
    assert result["code"] == "OK"
    assert result["ok"] is True
    run.assert_called_once()


def test_wildcard_allowlist_disables_check():
    """'*' in the allowlist bypasses the head-prefix check entirely."""
    with mock.patch("workers.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
        result = workers.run_isolated("some arbitrary tool", allowlist=("*",))
    assert result["code"] == "OK"
    run.assert_called_once()


def test_custom_allowlist_override():
    with mock.patch("workers.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
        result = workers.run_isolated("whoami", allowlist=("whoami",))
    assert result["code"] == "OK"
    run.assert_called_once()



# --------------------------------------------------------------------------- #
# subprocess execution                                                         #
# --------------------------------------------------------------------------- #
def test_success_zero_exit():
    with mock.patch("workers.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=0, stdout="1:2:3\n", stderr="")
        result = workers.run_isolated("uptime")
    assert result["ok"] is True
    assert result["code"] == "OK"
    assert result["output"] == "1:2:3\n"
    assert result["error"] == ""
    assert result["elapsed"] >= 0


def test_nonzero_exit_maps_to_exit_code():
    with mock.patch("workers.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=3, stdout="", stderr="boom")
        result = workers.run_isolated("false", allowlist=("*",))
    assert result["ok"] is False
    assert result["code"] == "EXIT_3"
    assert result["error"] == "boom"


def test_subprocess_passes_shell_and_capture_kwargs():
    with mock.patch("workers.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
        workers.run_isolated("hostname", timeout=12)
    run.assert_called_once()
    call = run.call_args
    assert call.args[0] == "hostname"
    assert call.kwargs.get("shell") is True
    assert call.kwargs.get("capture_output") is True
    assert call.kwargs.get("text") is True
    assert call.kwargs.get("timeout") == 12


def test_output_is_capped_at_output_cap():
    with mock.patch("workers.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=0, stdout="x" * 100, stderr="")
        result = workers.run_isolated("uptime", output_cap=10)


# --------------------------------------------------------------------------- #
# Exception mapping                                                            #
# --------------------------------------------------------------------------- #
def test_timeout_expired_maps_to_timeout():
    import subprocess
    with mock.patch("workers.subprocess.run",
                    side_effect=subprocess.TimeoutExpired(cmd="slow", timeout=5)):
        result = workers.run_isolated("slow", timeout=5, allowlist=("*",))
    assert result["ok"] is False
    assert result["code"] == "TIMEOUT"
    assert "timed out after 5s" in result["error"]


def test_arbitrary_exception_maps_to_internal():
    with mock.patch("workers.subprocess.run", side_effect=OSError("no fork")):
        result = workers.run_isolated("uptime")
    assert result["ok"] is False
    assert result["code"] == "INTERNAL"
    assert "no fork" in result["error"]


# --------------------------------------------------------------------------- #
# Result shape                                                                 #
# --------------------------------------------------------------------------- #
def test_result_contains_required_keys():
    with mock.patch("workers.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
        result = workers.run_isolated("hostname")
    assert {"ok", "output", "error", "code", "elapsed"} <= set(result)


def test_elapsed_is_float():
    with mock.patch("workers.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
        result = workers.run_isolated("hostname")
    assert isinstance(result["elapsed"], float)


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"FAIL  {name}: {exc}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)

    assert len(result["output"]) == 10


def test_stderr_is_capped_at_2000():
    with mock.patch("workers.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=1, stdout="", stderr="e" * 5000)
        result = workers.run_isolated("fail", allowlist=("*",))
    assert len(result["error"]) == 2000

