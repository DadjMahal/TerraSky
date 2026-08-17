"""Tests for sftp_client — SFTP file-manager client using mocked paramiko.

No real SSH server or key files are needed — paramiko is mocked.
"""
from __future__ import annotations

import base64
import os
import stat as stat_module
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sftp_client


# --------------------------------------------------------------------------- #
# Credential helpers                                                          #
# --------------------------------------------------------------------------- #
def test_get_ssh_key_path_env_override(monkeypatch):
    monkeypatch.setenv("HERMES_SSH_KEY_PATH", "/custom/key")
    assert sftp_client._get_ssh_key_path() == "/custom/key"


def test_get_ssh_key_path_default(monkeypatch):
    monkeypatch.delenv("HERMES_SSH_KEY_PATH", raising=False)
    assert sftp_client._get_ssh_key_path() == sftp_client.DEFAULT_SSH_KEY_PATH


def test_get_ssh_user_env_override(monkeypatch):
    monkeypatch.setenv("HERMES_SSH_USER", "myuser")
    assert sftp_client._get_ssh_user() == "myuser"


def test_get_ssh_user_default(monkeypatch):
    monkeypatch.delenv("HERMES_SSH_USER", raising=False)
    assert sftp_client._get_ssh_user() == sftp_client.DEFAULT_SSH_USER


def test_ssh_config_structure(monkeypatch):
    monkeypatch.setenv("HERMES_SSH_USER", "deploy")
    monkeypatch.setenv("HERMES_SSH_KEY_PATH", "/keys/id_ed25519")
    cfg = sftp_client.ssh_config("10.0.0.5")
    assert cfg["hostname"] == "10.0.0.5"
    assert cfg["username"] == "deploy"
    assert cfg["key_filename"] == "/keys/id_ed25519"
    assert cfg["timeout"] == 10
    assert cfg["look_for_keys"] is False


def test_ssh_config_no_env_uses_defaults(monkeypatch):
    monkeypatch.delenv("HERMES_SSH_USER", raising=False)
    monkeypatch.delenv("HERMES_SSH_KEY_PATH", raising=False)
    cfg = sftp_client.ssh_config("host1")
    assert cfg["username"] == "ubuntu"
    assert cfg["key_filename"] is None


# --------------------------------------------------------------------------- #
# _load_pkey                                                                  #
# --------------------------------------------------------------------------- #
@mock.patch("os.path.exists", return_value=False)
def test_load_pkey_missing_file_raises(mock_exists):
    with pytest.raises(FileNotFoundError, match="SSH key not found"):
        sftp_client._load_pkey("/nonexistent/key")


def test_load_pkey_rsa_success(tmp_path):
    """When RSAKey.from_private_key_file succeeds, return that key."""
    key_file = tmp_path / "id_rsa"
    key_file.write_text("fake")
    with mock.patch("os.path.exists", return_value=True), \
         mock.patch("paramiko.RSAKey.from_private_key_file", return_value="RSA_KEY") as mock_rsa, \
         mock.patch("paramiko.Ed25519Key.from_private_key_file") as mock_ed:
        result = sftp_client._load_pkey(str(key_file))
    assert result == "RSA_KEY"
    mock_rsa.assert_called_once_with(str(key_file))
    mock_ed.assert_not_called()


def test_load_pkey_ed25519_fallback(tmp_path):
    """If RSAKey fails with SSHException, try Ed25519Key."""
    import paramiko as real_paramiko
    key_file = tmp_path / "id_ed25519"
    key_file.write_text("fake")
    with mock.patch("os.path.exists", return_value=True), \
         mock.patch("paramiko.RSAKey.from_private_key_file",
                    side_effect=real_paramiko.SSHException("not rsa")), \
         mock.patch("paramiko.Ed25519Key.from_private_key_file",
                    return_value="ED25519_KEY") as mock_ed:
        result = sftp_client._load_pkey(str(key_file))
    assert result == "ED25519_KEY"
    mock_ed.assert_called_once_with(str(key_file))


def test_load_pkey_both_fail_raises_valueerror(tmp_path):
    """If neither RSA nor Ed25519 parses, raise ValueError."""
    import paramiko as real_paramiko
    key_file = tmp_path / "bad_key"
    key_file.write_text("fake")
    with mock.patch("os.path.exists", return_value=True), \
         mock.patch("paramiko.RSAKey.from_private_key_file",
                    side_effect=real_paramiko.SSHException("not rsa")), \
         mock.patch("paramiko.Ed25519Key.from_private_key_file",
                    side_effect=real_paramiko.SSHException("not ed25519")):
        with pytest.raises(ValueError, match="Could not parse SSH key"):
            sftp_client._load_pkey(str(key_file))

# --------------------------------------------------------------------------- #
# connect()                                                                   #
# --------------------------------------------------------------------------- #
@pytest.fixture
def mock_connection():
    """Patch paramiko.SSHClient and sftp_client._load_pkey so connect() is hermetic.

    Returns (mock_ssh_cls, mock_ssh, mock_sftp).
    """
    with mock.patch("paramiko.SSHClient") as mock_ssh_cls, \
         mock.patch.object(sftp_client, "_load_pkey", return_value=mock.Mock()) as mock_pkey:
        mock_ssh = mock_ssh_cls.return_value
        mock_sftp = mock_ssh.open_sftp.return_value
        yield mock_ssh_cls, mock_ssh, mock_sftp


def test_connect_success(mock_connection):
    mock_ssh_cls, mock_ssh, mock_sftp = mock_connection
    client, sftp = sftp_client.connect("10.0.0.1")
    mock_ssh.set_missing_host_key_policy.assert_called_once()
    _, kwargs = mock_ssh.connect.call_args
    assert kwargs["hostname"] == "10.0.0.1"
    assert kwargs["username"] == sftp_client.DEFAULT_SSH_USER
    assert kwargs["pkey"] is not None
    assert kwargs["timeout"] == 10
    assert kwargs["look_for_keys"] is False
    assert client is mock_ssh
    assert sftp is mock_sftp


def test_connect_uses_explicit_key_and_user(mock_connection, monkeypatch):
    _, mock_ssh, _ = mock_connection
    sftp_client.connect("10.0.0.1", key_path="/keys/custom", username="ops")
    _, kwargs = mock_ssh.connect.call_args
    assert kwargs["username"] == "ops"
    sftp_client._load_pkey.assert_called_once_with("/keys/custom")


def test_connect_raises_when_key_missing(mock_connection):
    sftp_client._load_pkey.side_effect = FileNotFoundError("SSH key not found")
    with pytest.raises(FileNotFoundError):
        sftp_client.connect("10.0.0.1")


# --------------------------------------------------------------------------- #
# Small helpers                                                               #
# --------------------------------------------------------------------------- #
def test_join():
    assert sftp_client._join("/base", "a", "b") == "/base/a/b"
    assert sftp_client._join("/base/", "/a//", "b") == "/base/a/b"
    assert sftp_client._join("", "a", "b") == "/a/b"


def test_iso_utc():
    assert sftp_client._iso(0) == "1970-01-01T00:00:00Z"


def test_cleanup_swallows_errors():
    bad = mock.Mock()
    bad.close.side_effect = IOError("boom")
    sftp_client._cleanup(bad, bad)  # must not raise
    bad.close.assert_called()


# --------------------------------------------------------------------------- #
# Public file operations (functional API)                                     #
# --------------------------------------------------------------------------- #
def _mkattr(filename, st_mode, size=1024):
    a = mock.Mock()
    a.filename = filename
    a.st_mode = st_mode
    a.st_size = size
    a.st_uid = 1000
    a.st_gid = 1000
    a.st_mtime = 0
    return a


def test_list_dir_returns_sorted_entries(mock_connection):
    _, _, mock_sftp = mock_connection
    mock_sftp.listdir_attr.return_value = [
        _mkattr("b.txt", 0o100644),
        _mkattr("a-dir", 0o40755),
    ]
    result = sftp_client.list_dir("10.0.0.1", "/home/ubuntu")
    assert result["ok"] is True
    entries = result["data"]["entries"]
    assert [e["name"] for e in entries] == ["a-dir", "b.txt"]  # dirs first
    assert entries[0]["type"] == "dir"
    assert entries[0]["display"] == "a-dir/"
    assert entries[1]["type"] == "file"
    assert entries[1]["path"] == "/home/ubuntu/b.txt"
    assert entries[1]["perms_octal"] == "644"
    assert entries[1]["mtime_iso"] == "1970-01-01T00:00:00Z"
    mock_sftp.listdir_attr.assert_called_once_with("/home/ubuntu")


def test_list_dir_error_returns_ok_false(mock_connection):
    _, _, mock_sftp = mock_connection
    mock_sftp.listdir_attr.side_effect = IOError("permission denied")
    result = sftp_client.list_dir("10.0.0.1", "/root")
    assert result["ok"] is False
    assert "permission denied" in result["error"]


def test_read_file_returns_decoded_content(mock_connection):
    _, _, mock_sftp = mock_connection
    mock_sftp.stat.return_value.st_size = 11
    mock_file = mock.Mock()
    mock_file.read.return_value = b"hello world"
    mock_sftp.open.return_value.__enter__ = mock.Mock(return_value=mock_file)
    mock_sftp.open.return_value.__exit__ = mock.Mock(return_value=False)
    result = sftp_client.read_file("10.0.0.1", "/tmp/a.txt")
    assert result["ok"] is True
    assert result["data"]["content"] == "hello world"
    assert result["data"]["size"] == 11
    assert result["data"]["truncated"] is False
    mock_file.set_pipelined.assert_called_once_with(True)


def test_read_file_marks_truncated_over_limit(mock_connection):
    _, _, mock_sftp = mock_connection
    mock_sftp.stat.return_value.st_size = 100
    mock_file = mock.Mock()
    mock_file.read.return_value = b"x" * 10
    mock_sftp.open.return_value.__enter__ = mock.Mock(return_value=mock_file)
    mock_sftp.open.return_value.__exit__ = mock.Mock(return_value=False)
    result = sftp_client.read_file("10.0.0.1", "/big.bin", limit=10)
    assert result["ok"] is True
    assert result["data"]["size"] == 100
    assert result["data"]["truncated"] is True
    mock_file.read.assert_called_once_with(10)


def test_read_file_missing_returns_error(mock_connection):
    _, _, mock_sftp = mock_connection
    mock_sftp.stat.side_effect = IOError("no such file")
    result = sftp_client.read_file("10.0.0.1", "/missing.txt")
    assert result["ok"] is False
    assert "no such file" in result["error"]


def test_write_file_writes_decoded_bytes(mock_connection):
    _, _, mock_sftp = mock_connection
    mock_file = mock.Mock()
    mock_sftp.open.return_value.__enter__ = mock.Mock(return_value=mock_file)
    mock_sftp.open.return_value.__exit__ = mock.Mock(return_value=False)
    result = sftp_client.write_file("10.0.0.1", "/tmp/out.txt", base64.b64encode(b"data").decode())
    assert result["ok"] is True
    assert result["data"]["bytes"] == 4
    assert result["data"]["path"] == "/tmp/out.txt"
    mock_file.write.assert_called_once_with(b"data")


def test_write_file_invalid_b64_returns_error(mock_connection):
    result = sftp_client.write_file("10.0.0.1", "/tmp/bad", "!!!not-base64!!!")
    assert result["ok"] is False
    assert "Invalid base64" in result["error"]


def test_write_file_sftp_error_returns_error(mock_connection):
    _, _, mock_sftp = mock_connection
    mock_sftp.open.side_effect = IOError("disk full")
    result = sftp_client.write_file("10.0.0.1", "/tmp/out.txt", base64.b64encode(b"x").decode())
    assert result["ok"] is False
    assert "disk full" in result["error"]


def test_delete_file_removes_regular_file(mock_connection):
    _, _, mock_sftp = mock_connection
    mock_sftp.stat.return_value.st_mode = 0o100644
    result = sftp_client.delete_file("10.0.0.1", "/tmp/a.txt")
    assert result["ok"] is True
    assert result["data"]["deleted"] is True
    mock_sftp.remove.assert_called_once_with("/tmp/a.txt")


def test_delete_file_recursively_removes_dir(mock_connection):
    _, _, mock_sftp = mock_connection
    mock_sftp.stat.return_value.st_mode = 0o40755
    mock_sftp.listdir_attr.return_value = []
    result = sftp_client.delete_file("10.0.0.1", "/tmp/dir")
    assert result["ok"] is True
    mock_sftp.rmdir.assert_called_once_with("/tmp/dir")


def test_delete_file_missing_returns_not_deleted(mock_connection):
    _, _, mock_sftp = mock_connection
    mock_sftp.stat.side_effect = FileNotFoundError("gone")
    result = sftp_client.delete_file("10.0.0.1", "/missing")
    assert result["ok"] is True
    assert result["data"]["deleted"] is False


def test_delete_file_error_returns_ok_false(mock_connection):
    _, _, mock_sftp = mock_connection
    mock_sftp.stat.side_effect = IOError("permission denied")
    result = sftp_client.delete_file("10.0.0.1", "/secret")
    assert result["ok"] is False
    assert "permission denied" in result["error"]


def test_stat_file_returns_metadata(mock_connection):
    _, _, mock_sftp = mock_connection
    st = mock.Mock()
    st.st_size = 1024
    st.st_mode = 0o100644
    st.st_uid = 1000
    st.st_gid = 1000
    st.st_mtime = 0
    mock_sftp.stat.return_value = st
    result = sftp_client.stat_file("10.0.0.1", "/etc/hosts")
    assert result["ok"] is True
    data = result["data"]
    assert data["path"] == "/etc/hosts"
    assert data["size"] == 1024
    assert data["perms_octal"] == "644"
    assert data["is_file"] is True
    assert data["is_dir"] is False
    assert data["mtime_iso"] == "1970-01-01T00:00:00Z"


def test_stat_file_error_returns_ok_false(mock_connection):
    _, _, mock_sftp = mock_connection
    mock_sftp.stat.side_effect = IOError("no such file")
    result = sftp_client.stat_file("10.0.0.1", "/missing")
    assert result["ok"] is False


def test_get_disk_usage_computes_percent(mock_connection):
    _, _, mock_sftp = mock_connection
    vfs = mock.Mock()
    vfs.f_frsize = 4096
    vfs.f_blocks = 1000
    vfs.f_bavail = 250
    mock_sftp.statvfs.return_value = vfs
    result = sftp_client.get_disk_usage("10.0.0.1", "/")
    assert result["ok"] is True
    data = result["data"]
    assert data["total"] == 4_096_000
    assert data["free"] == 1_024_000
    assert data["used"] == 3_072_000
    assert data["percent_used"] == 75.0


def test_get_disk_usage_error_returns_ok_false(mock_connection):
    _, _, mock_sftp = mock_connection
    mock_sftp.statvfs.side_effect = IOError("unsupported")
    result = sftp_client.get_disk_usage("10.0.0.1", "/")
    assert result["ok"] is False


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
