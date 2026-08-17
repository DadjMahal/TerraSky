"""Tests for hermes_agent — SSH-based log retrieval and system monitoring.

No real SSH server or key files are needed — paramiko and SSH helpers are mocked.
"""
from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hermes_agent


# --------------------------------------------------------------------------- #
# Credential helpers                                                          #
# --------------------------------------------------------------------------- #
def test_get_ssh_key_path_env_override(monkeypatch):
    monkeypatch.setenv("HERMES_SSH_KEY_PATH", "/custom/key")
    assert hermes_agent._get_ssh_key_path() == "/custom/key"


def test_get_ssh_key_path_default(monkeypatch):
    monkeypatch.delenv("HERMES_SSH_KEY_PATH", raising=False)
    assert hermes_agent._get_ssh_key_path() == hermes_agent.DEFAULT_SSH_KEY_PATH


def test_get_ssh_user_env_override(monkeypatch):
    monkeypatch.setenv("HERMES_SSH_USER", "hermes")
    assert hermes_agent._get_ssh_user() == "hermes"


def test_get_ssh_user_default(monkeypatch):
    monkeypatch.delenv("HERMES_SSH_USER", raising=False)


# --------------------------------------------------------------------------- #
# _run_command                                                               #
# --------------------------------------------------------------------------- #
def _fake_channel(exit_code=0, out=b"hello", err=b""):
    ch = mock.Mock()
    ch.recv_exit_status.return_value = exit_code
    return ch


def test_run_command_success():
    client = mock.Mock()
    stdout = mock.Mock()
    stdout.read.return_value = b"hello world"
    stdout.channel = _fake_channel(0)
    stderr = mock.Mock()
    stderr.read.return_value = b""
    client.exec_command.return_value = (mock.Mock(), stdout, stderr)

    result = hermes_agent._run_command(client, "echo hello")
    assert result["ok"] is True
    assert result["stdout"] == "hello world"
    assert result["exit_code"] == 0
    client.exec_command.assert_called_once_with("echo hello", timeout=15)


def test_run_command_nonzero_exit():
    client = mock.Mock()
    stdout = mock.Mock()
    stdout.read.return_value = b""
    stdout.channel = _fake_channel(1)
    stderr = mock.Mock()
    stderr.read.return_value = b"boom"
    client.exec_command.return_value = (mock.Mock(), stdout, stderr)

    result = hermes_agent._run_command(client, "false")
    assert result["ok"] is False
    assert result["exit_code"] == 1
    assert result["stderr"] == "boom"


def test_run_command_exception():
    client = mock.Mock()
    client.exec_command.side_effect = OSError("broken pipe")
    result = hermes_agent._run_command(client, "ls")
    assert result["ok"] is False
    assert "Command execution failed" in result["error"]


def test_run_command_respects_timeout():
    client = mock.Mock()
    stdout = mock.Mock()
    stdout.read.return_value = b""
    stdout.channel = _fake_channel(0)

# --------------------------------------------------------------------------- #
# _ssh_connect                                                               #
# --------------------------------------------------------------------------- #
def test_ssh_connect_success():
    with mock.patch("os.path.exists", return_value=True), \
         mock.patch("paramiko.RSAKey.from_private_key_file", return_value="RSA_KEY"), \
         mock.patch("paramiko.SSHClient") as mock_client_cls:
        client = mock_client_cls.return_value
        hermes_agent._ssh_connect("10.0.0.5", "/keys/id_rsa", "ubuntu")
        client.set_missing_host_key_policy.assert_called_once()
        client.connect.assert_called_once()
        call_kwargs = client.connect.call_args.kwargs
        assert call_kwargs["hostname"] == "10.0.0.5"
        assert call_kwargs["username"] == "ubuntu"
        assert call_kwargs["pkey"] == "RSA_KEY"
        assert call_kwargs["timeout"] == 10
        assert call_kwargs["look_for_keys"] is False


def test_ssh_connect_missing_key_file():
    with mock.patch("os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError, match="SSH key not found"):
            hermes_agent._ssh_connect("10.0.0.5")


def test_ssh_connect_ed25519_fallback():
    import paramiko as real_paramiko
    with mock.patch("os.path.exists", return_value=True), \
         mock.patch("paramiko.RSAKey.from_private_key_file",
                    side_effect=real_paramiko.SSHException("bad rsa")), \
         mock.patch("paramiko.Ed25519Key.from_private_key_file", return_value="ED_KEY"), \
         mock.patch("paramiko.SSHClient"):
        result = hermes_agent._ssh_connect("10.0.0.5", "/keys/id_ed25519")
        assert result is not None


def test_ssh_connect_key_parse_failure():
    import paramiko as real_paramiko
    with mock.patch("os.path.exists", return_value=True), \
         mock.patch("paramiko.RSAKey.from_private_key_file",
                    side_effect=real_paramiko.SSHException("bad rsa")), \
         mock.patch("paramiko.Ed25519Key.from_private_key_file",
                    side_effect=real_paramiko.SSHException("bad ed")):
        with pytest.raises(ValueError, match="Could not parse SSH key"):
            hermes_agent._ssh_connect("10.0.0.5", "/keys/bad")


def test_ssh_connect_auth_failure():
    import paramiko as real_paramiko
    client = mock.Mock()
    client.connect.side_effect = real_paramiko.AuthenticationException("denied")
    with mock.patch("os.path.exists", return_value=True), \
         mock.patch("paramiko.RSAKey.from_private_key_file", return_value="RSA_KEY"), \
         mock.patch("paramiko.SSHClient", return_value=client):
        with pytest.raises(PermissionError, match="SSH authentication failed"):
            hermes_agent._ssh_connect("10.0.0.5")


def test_ssh_connect_generic_failure():
    client = mock.Mock()
    client.connect.side_effect = OSError("network unreachable")

# --------------------------------------------------------------------------- #
# _check_service_status                                                      #
# --------------------------------------------------------------------------- #
def test_check_service_status_active():
    fake_client = mock.Mock()
    with mock.patch("hermes_agent._ssh_connect", return_value=fake_client), \
         mock.patch("hermes_agent._run_command",
                    return_value={"ok": True, "stdout": "active", "exit_code": 0, "stderr": ""}):
        result = hermes_agent._check_service_status("10.0.0.5")
    assert result["ok"] is True
    assert result["data"]["service"] == "hermes-agent"
    assert result["data"]["status"] == "active"
    fake_client.close.assert_called_once()


def test_check_service_status_error():
    fake_client = mock.Mock()
    with mock.patch("hermes_agent._ssh_connect", return_value=fake_client), \
         mock.patch("hermes_agent._run_command", return_value={"ok": False, "error": "x"}):
        result = hermes_agent._check_service_status("10.0.0.5")
    assert result["ok"] is True  # command itself succeeded; status is "unknown"
    assert result["data"]["status"] == "unknown"


def test_check_service_status_connect_failure():
    with mock.patch("hermes_agent._ssh_connect", side_effect=ConnectionError("no route")):
        result = hermes_agent._check_service_status("10.0.0.5")
    assert result["ok"] is False
    assert "no route" in result["error"]


# --------------------------------------------------------------------------- #
# Log fetchers                                                                #
# --------------------------------------------------------------------------- #
def _log_result(stdout="line1\nline2"):
    return {"ok": True, "stdout": stdout, "stderr": "", "exit_code": 0}


def test_fetch_gateway_logs_success_first_location():
    fake_client = mock.Mock()
    with mock.patch("hermes_agent._ssh_connect", return_value=fake_client), \
         mock.patch("hermes_agent._run_command",
                    return_value=_log_result("gateway log line\nsecond")) as mock_run:
        result = hermes_agent.fetch_gateway_logs("10.0.0.5", lines=25)
    assert result["ok"] is True
    assert result["data"]["line_count"] == 2
    assert result["data"]["logs"][0] == "gateway log line"
    # First command should reference the requested line count.
    assert mock_run.call_args.args[1] == "tail -25 ~/.hermes/logs/gateway.log 2>/dev/null"
    fake_client.close.assert_called_once()


def test_fetch_gateway_logs_falls_through_to_journalctl():
    fake_client = mock.Mock()
    outputs = [
        _log_result(""),  # first tail empty
        _log_result(""),  # second tail empty
        _log_result("journal line"),  # journalctl succeeds
    ]
    with mock.patch("hermes_agent._ssh_connect", return_value=fake_client), \
         mock.patch("hermes_agent._run_command", side_effect=outputs):
        result = hermes_agent.fetch_gateway_logs("10.0.0.5")
    assert result["ok"] is True
    assert result["data"]["source"] == "journalctl"
    assert result["data"]["logs"] == ["journal line"]


def test_fetch_gateway_logs_not_found():
    fake_client = mock.Mock()
    empty = _log_result("")
    with mock.patch("hermes_agent._ssh_connect", return_value=fake_client), \
         mock.patch("hermes_agent._run_command", return_value=empty):
        result = hermes_agent.fetch_gateway_logs("10.0.0.5")
    assert result["ok"] is False
    assert "not found" in result["error"]


def test_fetch_signal_logs_success():
    fake_client = mock.Mock()
    with mock.patch("hermes_agent._ssh_connect", return_value=fake_client), \
         mock.patch("hermes_agent._run_command",
                    return_value=_log_result("signal line")) as mock_run:
        result = hermes_agent.fetch_signal_logs("10.0.0.5", lines=50)
    assert result["ok"] is True
    assert result["data"]["logs"] == ["signal line"]
    assert "signal-cli.log" in mock_run.call_args.args[1]


def test_fetch_command_logs_success():
    fake_client = mock.Mock()
    with mock.patch("hermes_agent._ssh_connect", return_value=fake_client), \
         mock.patch("hermes_agent._run_command",
                    return_value=_log_result("cmd history")) as mock_run:
        result = hermes_agent.fetch_command_logs("10.0.0.5")
    assert result["ok"] is True
    assert result["data"]["logs"] == ["cmd history"]
    assert "agent.log" in mock_run.call_args.args[1]


def test_fetch_command_logs_find_fallback():
    fake_client = mock.Mock()
    outputs = [
        _log_result(""),  # agent.log empty
        _log_result(""),  # errors.log empty
        _log_result(""),  # commands.log empty
        _log_result(""),  # journalctl empty
        _log_result(""),  # ~/hermes/commands.log empty
        _log_result(""),  # execution_history empty
        _log_result("/var/log/hermes/a.log, /var/log/hermes/b.log"),
    ]
    with mock.patch("hermes_agent._ssh_connect", return_value=fake_client), \
         mock.patch("hermes_agent._run_command", side_effect=outputs):
        result = hermes_agent.fetch_command_logs("10.0.0.5")
    assert result["ok"] is False
    assert "Available" in result["error"]
    assert "a.log" in result["error"]

def test_fetch_all_logs_combines_sections():
    fake_client = mock.Mock()

    def run_side_effect(client, cmd, timeout=15):
        if "gateway.log" in cmd:
            return _log_result("gw1")
        if "signal" in cmd:
            return _log_result("sig1")
        return _log_result("")

    with mock.patch("hermes_agent._ssh_connect", return_value=fake_client), \
         mock.patch("hermes_agent._run_command", side_effect=run_side_effect):
        result = hermes_agent.fetch_all_logs("10.0.0.5", lines=10)
    assert result["ok"] is True
    assert result["data"]["gateway"] == ["gw1"]
    assert result["data"]["signal"] == ["sig1"]


def test_fetch_disk_status_parses_df():
    fake_client = mock.Mock()
    df_out = (
        "Filesystem Type Size Used Avail Use% Mounted\n"
        "/dev/sda1 ext4 100G 20G 80G 20% /\n"
    )
    du_out = "1.2G\t/var/log\n"
    inode_out = "/dev/sda1 12345 20% /\n"

    def run_side_effect(client, cmd, timeout=15):
        if "df -h" in cmd:
            return _log_result(df_out)
        if "du -sh" in cmd:
            return _log_result(du_out)
        if "df -i" in cmd:
            return _log_result(inode_out)
        return _log_result("")

    with mock.patch("hermes_agent._ssh_connect", return_value=fake_client), \
         mock.patch("hermes_agent._run_command", side_effect=run_side_effect):
        result = hermes_agent.fetch_disk_status("10.0.0.5")
    assert result["ok"] is True
    assert result["data"]["filesystems"][0]["filesystem"] == "/dev/sda1"
    assert result["data"]["filesystems"][0]["mounted_on"] == "/"
    assert result["data"]["directory_usage"][0] == {"path": "/var/log", "size": "1.2G"}
    assert result["data"]["inode_usage"][0]["filesystem"] == "/dev/sda1"

# --------------------------------------------------------------------------- #
# test_connection                                                            #
# --------------------------------------------------------------------------- #
def test_test_connection_success():
    fake_client = mock.Mock()
    key_path = "/tmp/fake_key_for_test"
    # Use a real temp key file so os.path.exists is True
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        key_path = tmp.name

    def run_side_effect(client, cmd, timeout=15):
        if "hermes not found" in cmd:
            return _log_result("hermes-agent 1.2.3")
        if "ls -la" in cmd:
            return _log_result("total 8\\n-rw-r--r-- 1 root root 10 gateway.log")
        if "tmux ls" in cmd:
            return _log_result("hermes: 1 windows")
        return _log_result("")

    try:
        with mock.patch("hermes_agent._ssh_connect", return_value=fake_client), \
             mock.patch("hermes_agent._get_ssh_key_path", return_value=key_path), \
             mock.patch("hermes_agent._run_command", side_effect=run_side_effect):
            result = hermes_agent.test_connection("10.0.0.5")
        assert result["ok"] is True
        assert result["checks"]["ssh_connection"] is True
        assert result["checks"]["ssh_key_exists"] is True
        assert result["checks"]["ssh_key_permissions_ok"] is True
        assert result["checks"]["hermes_agent_installed"] is True
        assert result["checks"]["hermes_agent_version"] == "hermes-agent 1.2.3"
        assert result["checks"]["log_directories_exist"] is True
        assert result["checks"]["tmux_sessions"] == "hermes: 1 windows"
        fake_client.close.assert_called_once()
    finally:
        os.unlink(key_path)


def test_test_connection_missing_key():
    with mock.patch("hermes_agent._get_ssh_key_path", return_value="/nonexistent/key"):
        result = hermes_agent.test_connection("10.0.0.5")
    assert result["ok"] is False
    assert result["checks"]["ssh_key_exists"] is False
    assert "ssh_connection" not in result["checks"] or result["checks"].get("ssh_connection") is not True


def test_test_connection_auth_failure():
    with mock.patch("hermes_agent._get_ssh_key_path", return_value="/tmp/fake_absent_key_xyz"), \
         mock.patch("hermes_agent._ssh_connect",
                    side_effect=PermissionError("SSH authentication failed")):
        result = hermes_agent.test_connection("10.0.0.5")
    assert result["ok"] is False
    assert "ssh_auth" in result["checks"]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))



def test_fetch_disk_status_df_failure():
    fake_client = mock.Mock()
    with mock.patch("hermes_agent._ssh_connect", return_value=fake_client), \
         mock.patch("hermes_agent._run_command",
                    return_value={"ok": False, "stdout": "", "stderr": "df: error", "exit_code": 1}):
        result = hermes_agent.fetch_disk_status("10.0.0.5")
    assert result["ok"] is False
    assert "Failed to get disk info" in result["error"]


    assert hermes_agent._get_ssh_user() == hermes_agent.DEFAULT_SSH_USER
