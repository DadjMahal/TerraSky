"""Tests for sftp_client — SFTP file-manager client using mocked paramiko.

No real SSH server or key files are needed — paramiko is mocked.
"""
from __future__ import annotations

import base64
import os
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
# SFTPClient — connect / close                                                 #
# --------------------------------------------------------------------------- #
@pytest.fixture
def mock_sftp_class():
    """Patch the module-level SSHClient / paramiko references."""
    with mock.patch("paramiko.SSHClient") as mock_ssh_cls, \
         mock.patch.object(sftp_client, "_load_pkey", return_value=mock.Mock()) as mock_pkey:
        mock_ssh = mock_ssh_cls.return_value
        # Make context manager return self
        mock_ssh.__enter__ = mock.Mock(return_value=mock_ssh)
        mock_ssh.__exit__ = mock.Mock(return_value=False)
        yield mock_ssh_cls, mock_ssh


def test_sftp_connect_success(mock_sftp_class):
    mock_ssh_cls, mock_ssh = mock_sftp_class
    client = sftp_client.SFTPClient("10.0.0.1")
    client.connect()
    mock_ssh.set_missing_host_key_policy.assert_called_once()
    mock_ssh.connect.assert_called_once()
    # Verify connect kwargs
    _, kwargs = mock_ssh.connect.call_args
    assert kwargs["hostname"] == "10.0.0.1"
    # _load_pkey was called (returns mock key)
    assert mock_ssh.connect.call_args[1]["pkey"] is not None


def test_sftp_close_calls_disconnect(mock_sftp_class):
    _, mock_ssh = mock_sftp_class
    client = sftp_client.SFTPClient("10.0.0.1")
    client.connect()
    client.close()
    mock_ssh.close.assert_called_once()


def test_sftp_context_manager_closes_on_exit(mock_sftp_class):
    mock_ssh_cls, mock_ssh = mock_sftp_class
    with sftp_client.SFTPClient("10.0.0.1") as client:
        assert client._ssh is mock_ssh
    mock_ssh.close.assert_called_once()


# --------------------------------------------------------------------------- #
# SFTPClient — file operations                                                 #
# --------------------------------------------------------------------------- #
@pytest.fixture
def connected_client(mock_sftp_class):
    _, mock_ssh = mock_sftp_class
    client = sftp_client.SFTPClient("10.0.0.1")
    client.connect()
    mock_sftp = mock_ssh.open_sftp.return_value
    client._sftp = mock_sftp
    return client


def test_sftp_mkdir_p_calls_makedirs(connected_client):
    connected_client._sftp.mkdir = mock.Mock()
    connected_client.mkdir_p("/remote/path/to/dir")
    connected_client._sftp.mkdir.assert_called()


def test_sftp_mkdir_p_existing_dir(connected_client):
    """If mkdir raises (dir exists), mkdir_p should not propagate the error."""
    import paramiko as real_paramiko
    connected_client._sftp.mkdir = mock.Mock(
        side_effect=real_paramiko.sftp.SFTPError("exists"))
    # Should not raise
    connected_client.mkdir_p("/exists")


def test_sftp_read_file(connected_client):
    mock_sftp = connected_client._sftp
    mock_file = mock.Mock()
    mock_file.read.return_value = b"file contents"
    mock_sftp.file.return_value.__enter__ = mock.Mock(return_value=mock_file)
    mock_sftp.file.return_value.__exit__ = mock.Mock(return_value=False)
    result = connected_client.read_file("/remote/file.txt")
    assert result == b"file contents"
    mock_file.read.assert_called_once()


def test_sftp_read_file_missing(connected_client):
    import paramiko as real_paramiko
    mock_sftp = connected_client._sftp
    mock_sftp.file.side_effect = real_paramiko.sftp.SFTPError("no such file")
    with pytest.raises(FileNotFoundError):
        connected_client.read_file("/missing.txt")


def test_sftp_write_file(connected_client):
    mock_sftp = connected_client._sftp
    mock_file = mock.Mock()
    mock_sftp.file.return_value.__enter__ = mock.Mock(return_value=mock_file)
    mock_sftp.file.return_value.__exit__ = mock.Mock(return_value=False)
    connected_client.write_file("/remote/file.txt", b"data")
    mock_file.write.assert_called_once_with(b"data")


def test_sftp_write_file_with_mkdir(connected_client):
    """write_file with make_dirs=True calls mkdir_p."""
    mock_sftp = connected_client._sftp
    mock_file = mock.Mock()
    mock_sftp.file.return_value.__enter__ = mock.Mock(return_value=mock_file)
    mock_sftp.file.return_value.__exit__ = mock.Mock(return_value=False)
    connected_client.mkdir_p = mock.Mock()
    connected_client.write_file("/remote/dir/file.txt", b"data", make_dirs=True)
    connected_client.mkdir_p.assert_called_once()
    mock_file.write.assert_called_once_with(b"data")


def test_sftp_list_dir(connected_client):
    mock_sftp = connected_client._sftp
    mock_sftp.listdir_attr.return_value = [
        mock.Mock(filename="file1.txt"),
        mock.Mock(filename="dir1/"),
    ]
    result = connected_client.list_dir("/remote/")
    assert [r["name"] for r in result] == ["file1.txt", "dir1/"]
    mock_sftp.listdir_attr.assert_called_once_with("/remote/")


def test_sftp_exists_file(connected_client):
    mock_sftp = connected_client._sftp
    mock_sftp.stat.return_value = mock.Mock()
    assert connected_client.exists("/remote/file.txt") is True
    mock_sftp.stat.assert_called_once_with("/remote/file.txt")


def test_sftp_exists_not_found(connected_client):
    import paramiko as real_paramiko
    mock_sftp = connected_client._sftp
    mock_sftp.stat.side_effect = real_paramiko.sftp.SFTPError("no such file")
    assert connected_client.exists("/missing") is False


def test_sftp_exists_returns_false_on_ioerror(connected_client):
    mock_sftp = connected_client._sftp
    mock_sftp.stat.side_effect = IOError("permission denied")
    assert connected_client.exists("/secret") is False


def test_sftp_remove(connected_client):
    mock_sftp = connected_client._sftp
    connected_client.remove("/remote/file.txt")
    mock_sftp.remove.assert_called_once_with("/remote/file.txt")


def test_sftp_rename(connected_client):
    mock_sftp = connected_client._sftp
    connected_client.rename("/remote/old.txt", "/remote/new.txt")
    mock_sftp.rename.assert_called_once_with("/remote/old.txt", "/remote/new.txt")


def test_sftp_stat(connected_client):
    mock_sftp = connected_client._sftp
    mock_stat = mock.Mock()
    mock_stat.st_size = 1024
    mock_sftp.stat.return_value = mock_stat
    result = connected_client.stat("/remote/file.txt")
    assert result.st_size == 1024
    mock_sftp.stat.assert_called_once_with("/remote/file.txt")


def test_sftp_close_without_connect():
    """close() must not raise if connect() was never called."""
    client = sftp_client.SFTPClient("10.0.0.1")
    assert client._ssh is None
    client.close()  # should not raise


def test_sftp_read_file_returns_bytes_on_empty_file(connected_client):
    mock_sftp = connected_client._sftp
    mock_file = mock.Mock()
    mock_file.read.return_value = b""
    mock_sftp.file.return_value.__enter__ = mock.Mock(return_value=mock_file)
    mock_sftp.file.return_value.__exit__ = mock.Mock(return_value=False)
    result = connected_client.read_file("/remote/empty.txt")
    assert result == b""


def test_sftp_write_file_ensure_parent_mkdirs(connected_client):
    """When make_dirs=True and a multi-level path is given, mkdir_p is called."""
    connected_client.mkdir_p = mock.Mock()
    mock_sftp = connected_client._sftp
    mock_file = mock.Mock()
    mock_sftp.file.return_value.__enter__ = mock.Mock(return_value=mock_file)
    mock_sftp.file.return_value.__exit__ = mock.Mock(return_value=False)
    connected_client.write_file("/a/b/c/file.txt", b"hello", make_dirs=True)
    mock_file.write.assert_called_once_with(b"hello")
    connected_client.mkdir_p.assert_called_once()


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
