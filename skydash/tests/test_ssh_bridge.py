"""Tests for ssh_bridge — interactive SSH terminal bridge (paramiko mocked).

No real SSH server or keys are needed: ``paramiko`` is replaced by a fake
module injected into ``sys.modules`` before the bridge is imported, and every
function is exercised against the fake channel/client objects.
"""
from __future__ import annotations

import os
import sys
import threading
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --------------------------------------------------------------------------- #
# Fake paramiko (injected into sys.modules before importing ssh_bridge)        #
# --------------------------------------------------------------------------- #
class FakeChannel:
    """Mimics the small paramiko Channel surface ssh_bridge touches."""

    def __init__(self, closed=False):
        self.closed = closed
        self._recv_ready = True
        self._exit_ready = False
        self._buf = b"hello\n"
        self.resize_calls = []

    def recv_ready(self):
        return self._recv_ready

    def exit_status_ready(self):
        return self._exit_ready

    def recv(self, n):
        # Real SFTP/SSH channels block on recv; mimic that so the bridge's
        # background _pump thread keeps the session alive (never returns empty).
        import time
        time.sleep(0.02)
        return b"x"

    def get_pty(self):
        return None

    def invoke_shell(self):
        return None

    def sendall(self, data):
        self.sent = data

    def resize_pty(self, width=None, height=None):
        self.resize_calls.append((width, height))

    def close(self):
        self.closed = True


class FakeClient:
    """Mimics paramiko.SSHClient enough for open_session."""

    def __init__(self, connect_error=None, channel_error=None):
        self.connect_error = connect_error
        self.channel_error = channel_error
        self.closed = False
        self._channel = None

    def set_missing_host_key_policy(self, policy):
        self.policy = policy

    def connect(self, **kwargs):
        self.kwargs = kwargs
        if self.connect_error:
            raise self.connect_error
        return None

    def get_transport(self):
        err = self.channel_error

        class _Transport:
            def open_session(self, term=None):
                if err:
                    raise err
                return FakeChannel()
        return _Transport()

    def open_sftp(self):
        return mock.Mock()

    def close(self):
        self.closed = True


class _FakeParamiko:
    """Stand-in module for ``import paramiko`` inside ssh_bridge."""

    class SSHClient(FakeClient):
        pass

    class AutoAddPolicy:
        pass

    class SSHException(Exception):
        pass


_pkg = type(sys)("paramiko")
_pkg.SSHClient = _FakeParamiko.SSHClient
_pkg.AutoAddPolicy = _FakeParamiko.AutoAddPolicy
_pkg.SSHException = _FakeParamiko.SSHException

if "paramiko" in sys.modules:
    _real = sys.modules["paramiko"]
else:
    _real = None
sys.modules["paramiko"] = _pkg

import ssh_bridge  # noqa: E402

# ssh_bridge keeps a reference to the fake module it imported, so its tests
# still work via mock.patch.object(ssh_bridge.paramiko, ...).  Restore the
# REAL paramiko in sys.modules so other test modules (e.g. test_sftp_client,
# which patches paramiko.RSAKey) are not broken by our fake.
if _real is not None:
    sys.modules["paramiko"] = _real
else:
    del sys.modules["paramiko"]


@pytest.fixture(autouse=True)
def _clean_sessions():
    """Every test starts with an empty session registry."""
    with ssh_bridge._lock:
        ssh_bridge._sessions.clear()
    yield
    with ssh_bridge._lock:
        ssh_bridge._sessions.clear()


# --------------------------------------------------------------------------- #
# _ssh_config                                                                 #
# --------------------------------------------------------------------------- #
def test_ssh_config_uses_env_overrides(monkeypatch):
    monkeypatch.setenv("HERMES_SSH_USER", "deploy")
    monkeypatch.setenv("HERMES_SSH_KEY_PATH", "/keys/id_ed25519")
    cfg = ssh_bridge._ssh_config("10.0.0.9")
    assert cfg["hostname"] == "10.0.0.9"
    assert cfg["username"] == "deploy"
    assert cfg["key_filename"] == "/keys/id_ed25519"
    assert cfg["timeout"] == 10


def test_ssh_config_defaults(monkeypatch):
    monkeypatch.delenv("HERMES_SSH_USER", raising=False)
    monkeypatch.delenv("HERMES_SSH_KEY_PATH", raising=False)
    cfg = ssh_bridge._ssh_config("host-a")
    assert cfg["username"] == "ubuntu"
    assert cfg["key_filename"] is None


# --------------------------------------------------------------------------- #
# new_sid                                                                     #
# --------------------------------------------------------------------------- #
def test_new_sid_returns_32_hex_chars():
    sid = ssh_bridge.new_sid()
    assert len(sid) == 32
    assert all(c in "0123456789abcdef" for c in sid)


def test_new_sid_unique():
    assert ssh_bridge.new_sid() != ssh_bridge.new_sid()


# --------------------------------------------------------------------------- #
# open_session                                                                 #
# --------------------------------------------------------------------------- #
class FakeSocketIO:
    def __init__(self):
        self.emitted = []

    def emit(self, event, payload, to=None, namespace=None):
        self.emitted.append((event, payload, to, namespace))


def test_open_session_success_emits_ok():
    sio = FakeSocketIO()
    with mock.patch.object(ssh_bridge.paramiko, "SSHClient",
                           return_value=_FakeParamiko.SSHClient()):
        ok = ssh_bridge.open_session("sid1", "10.0.0.1", sio, "/ns")
    assert ok is True
    events = [e[0] for e in sio.emitted]
    assert "ssh_status" in events
    status = [e[1] for e in sio.emitted if e[0] == "ssh_status"][0]
    assert status["ok"] is True
    assert status["host"] == "10.0.0.1"
    with ssh_bridge._lock:
        assert "sid1" in ssh_bridge._sessions
        thread = ssh_bridge._sessions["sid1"]["thread"]
    assert isinstance(thread, threading.Thread)


def test_open_session_connect_failure_emits_error():
    sio = FakeSocketIO()
    client = _FakeParamiko.SSHClient(connect_error=OSError("refused"))
    with mock.patch.object(ssh_bridge.paramiko, "SSHClient", return_value=client):
        ok = ssh_bridge.open_session("sid2", "10.0.0.2", sio, "/ns")
    assert ok is False
    status = [e[1] for e in sio.emitted if e[0] == "ssh_status"][0]
    assert status["ok"] is False
    assert "SSH connection failed" in status["error"]
    with ssh_bridge._lock:
        assert "sid2" not in ssh_bridge._sessions


def test_open_session_channel_failure_closes_client():
    sio = FakeSocketIO()
    client = _FakeParamiko.SSHClient(channel_error=OSError("no channel"))
    with mock.patch.object(ssh_bridge.paramiko, "SSHClient", return_value=client):
        ok = ssh_bridge.open_session("sid3", "10.0.0.3", sio, "/ns")
    assert ok is False
    assert client.closed is True
    status = [e[1] for e in sio.emitted if e[0] == "ssh_status"][0]
    assert status["ok"] is False
    assert "Shell open failed" in status["error"]


def test_open_session_replaces_existing_session():
    """open_session calls close_session first — the old sid entry is gone."""
    sio = FakeSocketIO()
    with ssh_bridge._lock:
        ssh_bridge._sessions["sid4"] = {
            "channel": FakeChannel(closed=True),
            "client": _FakeParamiko.SSHClient(),
        }
    with mock.patch.object(ssh_bridge.paramiko, "SSHClient",
                           return_value=_FakeParamiko.SSHClient()):
        ok = ssh_bridge.open_session("sid4", "10.0.0.4", sio, "/ns")
    assert ok is True
    with ssh_bridge._lock:
        assert "sid4" in ssh_bridge._sessions
        assert "thread" in ssh_bridge._sessions["sid4"]


# --------------------------------------------------------------------------- #
# send_input / resize / close_session                                          #
# --------------------------------------------------------------------------- #
def test_send_input_writes_to_channel():
    chan = FakeChannel()
    with ssh_bridge._lock:
        ssh_bridge._sessions["s"] = {"channel": chan, "client": mock.Mock()}
    ssh_bridge.send_input("s", "ls -la")
    assert chan.sent == b"ls -la"


def test_send_input_ignores_unknown_sid():
    ssh_bridge.send_input("nope", "x")  # must not raise


def test_send_input_ignores_closed_channel():
    chan = FakeChannel(closed=True)
    with ssh_bridge._lock:
        ssh_bridge._sessions["s"] = {"channel": chan, "client": mock.Mock()}
    ssh_bridge.send_input("s", "data")  # must not raise
    assert not hasattr(chan, "sent")


def test_resize_calls_resize_pty():
    chan = FakeChannel()
    with ssh_bridge._lock:
        ssh_bridge._sessions["s"] = {"channel": chan, "client": mock.Mock()}
    ssh_bridge.resize("s", 120, 40)
    assert chan.resize_calls == [(120, 40)]


def test_resize_swallows_errors():
    class BadChannel:
        closed = False

        def resize_pty(self, **kw):
            raise OSError("boom")

    with ssh_bridge._lock:
        ssh_bridge._sessions["s"] = {"channel": BadChannel(), "client": mock.Mock()}
    ssh_bridge.resize("s", 80, 24)  # must not raise


def test_close_session_closes_channel_and_client():
    chan = FakeChannel()
    client = _FakeParamiko.SSHClient()
    with ssh_bridge._lock:
        ssh_bridge._sessions["s"] = {"channel": chan, "client": client}
    ssh_bridge.close_session("s")
    assert chan.closed is True
    assert client.closed is True
    with ssh_bridge._lock:
        assert "s" not in ssh_bridge._sessions


def test_close_session_unknown_sid_is_noop():
    ssh_bridge.close_session("missing")  # must not raise
    with ssh_bridge._lock:
        assert "missing" not in ssh_bridge._sessions


def test_close_session_swallows_close_errors():
    class Bad:
        def close(self):
            raise OSError("boom")

    with ssh_bridge._lock:
        ssh_bridge._sessions["s"] = {"channel": Bad(), "client": Bad()}
    ssh_bridge.close_session("s")  # must not raise


if __name__ == "__main__":
    import pytest as _pytest

    sys.exit(_pytest.main([__file__, "-v"]))

