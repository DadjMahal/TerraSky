"""SFTP file manager client (§20 — File manager feature).

Provides SFTP-backed file operations (list / read / write / delete / stat / disk)
on top of an existing paramiko ``SSHClient``.  This mirrors the SSH bridge /
Hermes agent pattern in ``ssh_bridge.py`` and ``hermes_agent.py``:

* Paramiko is imported **lazily** inside the connect path so the app stays
  lightweight when the file-manager tab is inactive.
* SSH credentials are resolved from environment variables, the same ones shared
  with the Hermes SSH terminal (§16):

      HERMES_SSH_KEY_PATH  — path to the SSH private key (default: ~/.ssh/id_rsa)
      HERMES_SSH_USER      — SSH username (default: ubuntu)

  The host is the instance's live ``public_ip`` (resolved by the Flask route
  from the provider / Terraform state), exactly as ``ssh_bridge.open_session``
  and ``custom_ssh.py`` do.

**Command contract** — this module implements the operations described by
``skydash/features/files.py`` (list_dir, read_file, write_file, delete_file,
stat) using real SFTP calls instead of the scaffolded ``ls``/``head``/``rm``
shell commands.  Each method returns a dict with at minimum::

    {"ok": bool, "data": ..., "error": str}

Connection errors are handled gracefully — they never raise past the public
methods, so the Flask layer can simply forward the ``{"ok": False, "error": ...}``
dict as a JSON error response.
"""
from __future__ import annotations

import os
import stat as stat_module
from typing import Any

# Hard ceiling for read_file so a single request can't pull a multi-GB file
# through the browser.  Matches features.files.LIMITS["max_upload_bytes"] for
# write; reads are capped to a generous 1 MiB to keep responses snappy.
MAX_READ_BYTES = 1 * 1024 * 1024  # 1 MiB

# These mirror hermes_agent / ssh_bridge defaults so every SSH path resolves
# credentials identically (HERMES_SSH_KEY_PATH / HERMES_SSH_USER).
DEFAULT_SSH_USER = "ubuntu"
DEFAULT_SSH_KEY_PATH = os.path.expanduser("~/.ssh/id_rsa")


def _get_ssh_key_path() -> str:
    """Return the configured SSH private-key path (env override or default)."""
    return os.environ.get("HERMES_SSH_KEY_PATH", DEFAULT_SSH_KEY_PATH)


def _get_ssh_user() -> str:
    """Return the configured SSH username (env override or default)."""
    return os.environ.get("HERMES_SSH_USER", DEFAULT_SSH_USER)


def ssh_config(host: str) -> dict:
    """Build a paramiko ``connect()`` keyword dict for *host*.

    Mirrors ``ssh_bridge._ssh_config`` and ``hermes_agent._ssh_connect`` so the
    file-manager uses exactly the same credential resolution as the SSH terminal.
    """
    return {
        "hostname": host,
        "username": os.environ.get("HERMES_SSH_USER", DEFAULT_SSH_USER),
        "key_filename": os.environ.get("HERMES_SSH_KEY_PATH") or None,
        "timeout": 10,
        "look_for_keys": False,
    }


def _load_pkey(key_path: str) -> Any:
    """Parse an RSA or Ed25519 private key from *key_path*.

    Returns a paramiko PKey subclass instance suitable for ``SSHClient.connect``.
    Raises ``FileNotFoundError`` if the key file is missing and ``ValueError``
    if it can't be parsed as RSA or Ed25519 — both are caught by callers.
    """
    import paramiko  # lazy (matches hermes_agent._ssh_connect)

    if not os.path.exists(key_path):
        raise FileNotFoundError(
            f"SSH key not found at {key_path}. "
            f"Configure HERMES_SSH_KEY_PATH or generate an SSH key."
        )
    try:
        return paramiko.RSAKey.from_private_key_file(key_path)
    except paramiko.SSHException:
        try:
            return paramiko.Ed25519Key.from_private_key_file(key_path)
        except paramiko.SSHException:
            raise ValueError(
                f"Could not parse SSH key at {key_path}. "
                "Ensure it is a valid RSA or Ed25519 private key."
            )


def connect(host: str, key_path: str | None = None, username: str | None = None) -> tuple:
    """Open an SSHClient to *host* and return ``(client, sftp)``.

    On any failure raises a descriptive exception (FileNotFoundError /
    PermissionError / ConnectionError) — callers wrap in try/except and return
    the standard ``{"ok": False, "error": ...}`` envelope.
    """
    import paramiko  # lazy

    key_path = key_path or _get_ssh_key_path()
    username = username or _get_ssh_user()

    key = _load_pkey(key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        username=username,
        pkey=key,
        timeout=10,
        look_for_keys=False,
    )
    sftp = client.open_sftp()
    return client, sftp


def _connect(host: str, key_path: str | None = None, username: str | None = None) -> tuple:
    """Alias of :func:`connect` used by the public methods below."""
    return connect(host, key_path=key_path, username=username)


def _join(base: str, *parts: str) -> str:
    """Join SFTP path components the way os.path.join works locally."""
    if not base:
        return "/" + "/".join(p.strip("/") for p in parts if p)
    parts = [base.rstrip("/")] + [p.strip("/") for p in parts if p]
    return "/".join(parts)


def _cleanup(client: Any, sftp: Any) -> None:
    """Close SFTP channel and SSH client, swallowing errors (best-effort)."""
    for obj in (sftp, client):
        if obj is not None:
            try:
                obj.close()
            except Exception:  # noqa: BLE001 — cleanup must never raise
                pass


def _iso(epoch: float) -> str:
    """Format a Unix epoch as an ISO-8601 UTC string."""
    import time as _time
    return _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime(epoch))


# ---------------------------------------------------------------------------
# Public file-manager operations — implement the features/files.py COMMANDS
# contract (list_dir, read_file, write_file, delete_file, stat) over SFTP.
# ---------------------------------------------------------------------------

def list_dir(host: str, path: str, key_path: str | None = None,
             username: str | None = None) -> dict:
    """List the contents of *path* on *host*.

    Returns ``{"ok": True, "data": {"entries": [...]}}`` where each entry is::

        {"name", "type", "size", "permissions", "perms_octal",
         "owner", "group", "mtime", "mtime_iso", "path", "display"}

    On failure returns ``{"ok": False, "error": str}``.
    """
    client = sftp = None
    try:
        client, sftp = _connect(host, key_path, username)
        entries = []
        for info in sftp.listdir_attr(path):
            fpath = _join(path, info.filename)
            is_dir = stat_module.S_ISDIR(info.st_mode)
            entries.append({
                "name": info.filename,
                "type": "dir" if is_dir else "file",
                "size": info.st_size,
                "permissions": stat_module.filemode(info.st_mode),
                "perms_octal": oct(info.st_mode & 0o777)[2:].zfill(3),
                "owner": info.st_uid,
                "group": info.st_gid,
                "mtime": info.st_mtime,
                "mtime_iso": _iso(info.st_mtime),
                "path": fpath,
                "display": info.filename + ("/" if is_dir else ""),
            })
        entries.sort(key=lambda e: (e["type"] != "dir", e["name"]))
        return {"ok": True, "data": {"entries": entries}}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
    finally:
        _cleanup(client, sftp)


def read_file(host: str, path: str, limit: int = 0,
              key_path: str | None = None, username: str | None = None) -> dict:
    """Read up to *limit* bytes from *path* on *host*.

    If *limit* is 0 or omitted the content is truncated to
    :data:`MAX_READ_BYTES` (1 MiB).  Returns::

        {"ok": True, "data": {"content": str, "size": int, "truncated": bool}}
    """
    client = sftp = None
    try:
        client, sftp = _connect(host, key_path, username)
        st = sftp.stat(path)
        size = st.st_size
        limit = int(limit) if limit else 0
        if limit > 0:
            read_bytes = limit
        else:
            read_bytes = min(size, MAX_READ_BYTES)
            limit = read_bytes

        truncated = size > read_bytes
        with sftp.open(path, "r") as f:
            f.set_pipelined(True)
            raw = f.read(read_bytes)
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("latin-1")
        return {"ok": True, "data": {"content": content, "size": size, "truncated": truncated}}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
    finally:
        _cleanup(client, sftp)


def write_file(host: str, path: str, content_b64: str,
               key_path: str | None = None, username: str | None = None) -> dict:
    """Write base64-encoded *content_b64* to *path* on *host*.

    Returns ``{"ok": True, "data": {"bytes": int, "path": str}}``.
    """
    import base64  # stdlib

    client = sftp = None
    try:
        raw = base64.b64decode(content_b64, validate=True)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"Invalid base64 content: {e}"}
    try:
        client, sftp = _connect(host, key_path, username)
        with sftp.open(path, "w") as f:
            f.set_pipelined(True)
            f.write(raw)
        return {"ok": True, "data": {"bytes": len(raw), "path": path}}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
    finally:
        _cleanup(client, sftp)


def delete_file(host: str, path: str,
                key_path: str | None = None, username: str | None = None) -> dict:
    """Delete the file or directory at *path* on *host*.

    Directories are removed recursively.  Returns
    ``{"ok": True, "data": {"deleted": bool, "path": str}}``.
    """
    client = sftp = None
    try:
        client, sftp = _connect(host, key_path, username)
        st = sftp.stat(path)
        if stat_module.S_ISDIR(st.st_mode):
            _sftp_rmtree(sftp, path)
        else:
            sftp.remove(path)
        return {"ok": True, "data": {"deleted": True, "path": path}}
    except FileNotFoundError:
        return {"ok": True, "data": {"deleted": False, "path": path}}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
    finally:
        _cleanup(client, sftp)


def _sftp_rmtree(sftp: Any, path: str) -> None:
    """Recursively remove a directory and its contents (via *open* SFTP channel)."""
    for entry in sftp.listdir_attr(path):
        child = _join(path, entry.filename)
        if stat_module.S_ISDIR(entry.st_mode):
            _sftp_rmtree(sftp, child)
        else:
            sftp.remove(child)
    sftp.rmdir(path)


def stat_file(host: str, path: str,
              key_path: str | None = None, username: str | None = None) -> dict:
    """Return stat metadata for *path* on *host*.

    Returns ``{"ok": True, "data": {stat fields}}`` following the
    features/files.py ``stat`` command contract.
    """
    client = sftp = None
    try:
        client, sftp = _connect(host, key_path, username)
        st = sftp.stat(path)
        return {"ok": True, "data": {
            "path": path,
            "size": st.st_size,
            "permissions": stat_module.filemode(st.st_mode),
            "perms_octal": oct(st.st_mode & 0o777)[2:].zfill(3),
            "owner": st.st_uid,
            "group": st.st_gid,
            "mtime": st.st_mtime,
            "mtime_iso": _iso(st.st_mtime),
            "is_dir": stat_module.S_ISDIR(st.st_mode),
            "is_file": stat_module.S_ISREG(st.st_mode),
        }}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
    finally:
        _cleanup(client, sftp)


def get_disk_usage(host: str, path: str = "/",
                   key_path: str | None = None, username: str | None = None) -> dict:
    """Return filesystem disk usage for the partition containing *path*.

    Uses ``statvfs`` over the SFTP channel — paramiko's ``SFTPClient.statvfs``
    requires a remote SFTP server that supports the extension.  Returns
    ``{"ok": True, "data": {"path": str, "total": int, "used": int,
    "free": int, "percent_used": float}}``.
    """
    client = sftp = None
    try:
        client, sftp = _connect(host, key_path, username)
        vfs = sftp.statvfs(path)
        total = vfs.f_frsize * vfs.f_blocks
        free = vfs.f_frsize * vfs.f_bavail
        used = total - free
        pct = round((used / total) * 100, 1) if total > 0 else 0.0
        return {"ok": True, "data": {
            "path": path,
            "total": total,
            "used": used,
            "free": free,
            "percent_used": pct,
        }}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
    finally:
        _cleanup(client, sftp)
