"""Interactive SSH terminal bridge for the built-in web terminal (#16).

Bridges an xterm.js front-end (over Socket.IO) to a live paramiko SSH channel.
The front-end emits ``ssh_input`` (bytes typed) and ``ssh_resize`` (cols/rows);
this module streams ``ssh_output`` (channel output) and ``ssh_status`` back.

Connection details come from environment variables (shared with hermes_agent):
    HERMES_SSH_KEY_PATH, HERMES_SSH_USER (default ubuntu), HERMES_SSH_HOST override.
The host defaults to the instance's live public IP (resolved via the provider).

This runs in background threads (one per terminal session). The threading
async_mode of Flask-SocketIO lets us emit from these worker threads.
"""
from __future__ import annotations

import logging
import os
import threading
import uuid

import paramiko

logger = logging.getLogger(__name__)

# sid -> {"channel": Channel, "client": SSHClient, "thread": Thread}
_sessions: dict[str, dict] = {}
_lock = threading.Lock()


def _ssh_config(host: str) -> dict:
    return {
        "hostname": host,
        "username": os.environ.get("HERMES_SSH_USER", "ubuntu"),
        "key_filename": os.environ.get("HERMES_SSH_KEY_PATH") or None,
        "timeout": 10,
    }


def open_session(sid: str, host: str, socketio, namespace: str) -> bool:
    """Open a new interactive SSH session for `sid` to `host`."""
    close_session(sid)
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(**_ssh_config(host))
    except Exception as e:  # noqa: BLE001
        logger.error("SSH connect to %s failed: %s", host, e)
        socketio.emit("ssh_status", {"ok": False, "error": f"SSH connection failed: {e}"},
                      to=sid, namespace=namespace)
        return False

    try:
        chan = client.get_transport().open_session(term="xterm-256color")
        chan.get_pty()
        chan.invoke_shell()
    except Exception as e:  # noqa: BLE001
        logger.error("SSH channel open failed: %s", e)
        socketio.emit("ssh_status", {"ok": False, "error": f"Shell open failed: {e}"},
                      to=sid, namespace=namespace)
        client.close()
        return False

    with _lock:
        _sessions[sid] = {"channel": chan, "client": client, "host": host}

    socketio.emit("ssh_status", {"ok": True, "host": host}, to=sid, namespace=namespace)

    def _pump():
        try:
            while not chan.recv_ready() is False and not chan.exit_status_ready():
                if chan.recv_ready():
                    data = chan.recv(4096)
                    if not data:
                        break
                    socketio.emit("ssh_output", {"data": data.decode("utf-8", "replace")},
                                  to=sid, namespace=namespace)
                else:
                    import time
                    time.sleep(0.05)
        except Exception as e:  # noqa: BLE001
            socketio.emit("ssh_output", {"data": f"\r\n[disconnected: {e}]\r\n"},
                          to=sid, namespace=namespace)
        finally:
            socketio.emit("ssh_status", {"ok": False, "error": "session ended"},
                          to=sid, namespace=namespace)
            close_session(sid)

    t = threading.Thread(target=_pump, daemon=True)
    _sessions[sid]["thread"] = t
    t.start()
    return True


def send_input(sid: str, data: str) -> None:
    with _lock:
        s = _sessions.get(sid)
    if s and s["channel"] and not s["channel"].closed:
        try:
            s["channel"].sendall(data.encode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            logger.warning("ssh send_input failed: %s", e)


def resize(sid: str, cols: int, rows: int) -> None:
    with _lock:
        s = _sessions.get(sid)
    if s and s["channel"] and not s["channel"].closed:
        try:
            s["channel"].resize_pty(width=cols, height=rows)
        except Exception:  # noqa: BLE001
            pass


def close_session(sid: str) -> None:
    with _lock:
        s = _sessions.pop(sid, None)
    if not s:
        return
    try:
        s["channel"].close()
    except Exception:  # noqa: BLE001
        pass
    try:
        s["client"].close()
    except Exception:  # noqa: BLE001
        pass


def new_sid() -> str:
    return uuid.uuid4().hex
