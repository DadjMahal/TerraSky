"""Hermes Agent — SSH-based log retrieval and system monitoring for the Hermes server.

Connects to the Hermes AWS EC2 instance via SSH (paramiko) to fetch:
- Hermes Gateway logs
- Signal-Cli logs
- Command execution logs (tracked by the Hermes Agent)
- Combined system logs
- Disk usage statistics

SSH credentials are configured via environment variables:
  HERMES_SSH_KEY_PATH  — path to the SSH private key (default: ~/.ssh/id_rsa)
  HERMES_SSH_USER      — SSH username (default: ubuntu)
  HERMES_SSH_HOST      — SSH hostname/IP (default: uses instance's public IP)

All methods return a dict with at minimum:
  {"ok": bool, "data": ..., "error": str}
"""
from __future__ import annotations

import os
import stat as stat_module
from typing import Any

# Paramiko is imported lazily inside methods to keep the app lightweight

# Default SSH configuration
DEFAULT_SSH_USER = "ubuntu"
DEFAULT_SSH_KEY_PATH = os.path.expanduser("~/.ssh/id_rsa")


def _get_ssh_key_path() -> str:
    return os.environ.get("HERMES_SSH_KEY_PATH", DEFAULT_SSH_KEY_PATH)


def _get_ssh_user() -> str:
    return os.environ.get("HERMES_SSH_USER", DEFAULT_SSH_USER)


def _ssh_connect(host: str, key_path: str | None = None, username: str | None = None) -> Any:
    """Establish an SSH connection to the given host.
    
    Returns the SSH client on success.
    Raises a descriptive exception on failure.
    """
    import paramiko
    
    key_path = key_path or _get_ssh_key_path()
    username = username or _get_ssh_user()
    
    if not os.path.exists(key_path):
        raise FileNotFoundError(
            f"SSH key not found at {key_path}. "
            f"Configure HERMES_SSH_KEY_PATH in .env or generate an SSH key."
        )
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        key = paramiko.RSAKey.from_private_key_file(key_path)
    except paramiko.SSHException:
        try:
            key = paramiko.Ed25519Key.from_private_key_file(key_path)
        except paramiko.SSHException:
            raise ValueError(
                f"Could not parse SSH key at {key_path}. "
                f"Ensure it is a valid RSA or Ed25519 private key."
            )
    
    try:
        client.connect(
            hostname=host,
            username=username,
            pkey=key,
            timeout=10,
            look_for_keys=False,
        )
    except paramiko.AuthenticationException:
        raise PermissionError(
            f"SSH authentication failed for {username}@{host}. "
            f"Ensure the public key is added to ~/.ssh/authorized_keys on the server."
        )
    except paramiko.SSHException as e:
        raise ConnectionError(f"SSH connection failed to {host}: {e}")
    except Exception as e:
        raise ConnectionError(f"Could not connect to {host}: {e}")
    
    return client


def _run_command(client: Any, command: str, timeout: int = 15) -> dict:
    """Run a command over SSH and return its output.
    
    Returns:
        {"ok": True, "stdout": str, "stderr": str, "exit_code": int}
        or {"ok": False, "error": str}
    """
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        return {"ok": exit_code == 0, "stdout": out, "stderr": err, "exit_code": exit_code}
    except Exception as e:
        return {"ok": False, "error": f"Command execution failed: {e}"}


def _check_service_status(host: str) -> dict:
    """Check if Hermes Agent service is running on the server."""
    key_path = _get_ssh_key_path()
    username = _get_ssh_user()
    client = None
    try:
        client = _ssh_connect(host, key_path, username)
        result = _run_command(client, "systemctl is-active hermes-agent 2>/dev/null || echo 'inactive'")
        return {"ok": True, "data": {"service": "hermes-agent", "status": result.get("stdout", "unknown")}}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if client:
            client.close()


def fetch_gateway_logs(host: str, lines: int = 100) -> dict:
    """Fetch Hermes Gateway work logs.
    
    Tries multiple possible log locations:
    1. /var/log/hermes/gateway.log
    2. journalctl -u hermes-gateway
    3. ~/hermes/gateway.log
    """
    commands = [
        f"tail -{lines} ~/.hermes/logs/gateway.log 2>/dev/null",
        f"tail -{lines} /var/log/hermes/gateway.log 2>/dev/null",
        f"journalctl -u hermes-gateway --no-pager -n {lines} 2>/dev/null",
        f"tail -{lines} ~/hermes/gateway.log 2>/dev/null",
    ]
    key_path = _get_ssh_key_path()
    username = _get_ssh_user()
    client = None
    try:
        client = _ssh_connect(host, key_path, username)
        for cmd in commands:
            result = _run_command(client, cmd)
            if result["ok"] and result.get("stdout"):
                return {
                    "ok": True,
                    "data": {
                        "source": cmd.split()[2] if cmd.startswith("tail") else "journalctl",
                        "logs": result["stdout"].split("\n"),
                        "line_count": len(result["stdout"].split("\n")),
                    },
                }
        return {"ok": False, "error": "Hermes Gateway logs not found on the server."}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if client:
            client.close()


def fetch_signal_logs(host: str, lines: int = 100) -> dict:
    """Fetch Signal-Cli work logs.
    
    Tries multiple possible log locations:
    1. /var/log/hermes/signal-cli.log
    2. journalctl -u hermes-signal
    3. ~/hermes/signal-cli.log
    """
    commands = [
        f"tail -{lines} ~/.hermes/logs/signal-cli.log 2>/dev/null",
        f"grep -i 'signal' ~/.hermes/logs/gateway.log 2>/dev/null | tail -{lines}",
        f"tail -{lines} /var/log/hermes/signal-cli.log 2>/dev/null",
        f"journalctl -u hermes-signal --no-pager -n {lines} 2>/dev/null",
        f"tail -{lines} ~/hermes/signal-cli.log 2>/dev/null",
    ]
    key_path = _get_ssh_key_path()
    username = _get_ssh_user()
    client = None
    try:
        client = _ssh_connect(host, key_path, username)
        for cmd in commands:
            result = _run_command(client, cmd)
            if result["ok"] and result.get("stdout"):
                return {
                    "ok": True,
                    "data": {
                        "source": cmd.split()[2] if cmd.startswith("tail") else "journalctl",
                        "logs": result["stdout"].split("\n"),
                        "line_count": len(result["stdout"].split("\n")),
                    },
                }
        return {"ok": False, "error": "Signal-Cli logs not found on the server."}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if client:
            client.close()


def fetch_command_logs(host: str, lines: int = 100) -> dict:
    """Fetch command execution logs tracked by the Hermes Agent.
    
    Tries multiple possible log locations:
    1. /var/log/hermes/commands.log
    2. journalctl -u hermes-agent
    3. ~/hermes/commands.log
    4. ~/hermes/execution_history.log
    """
    commands = [
        f"tail -{lines} ~/.hermes/logs/agent.log 2>/dev/null",
        f"tail -{lines} ~/.hermes/logs/errors.log 2>/dev/null",
        f"tail -{lines} /var/log/hermes/commands.log 2>/dev/null",
        f"journalctl -u hermes-agent --no-pager -n {lines} 2>/dev/null",
        f"tail -{lines} ~/hermes/commands.log 2>/dev/null",
        f"tail -{lines} ~/hermes/execution_history.log 2>/dev/null",
    ]
    key_path = _get_ssh_key_path()
    username = _get_ssh_user()
    client = None
    try:
        client = _ssh_connect(host, key_path, username)
        for cmd in commands:
            result = _run_command(client, cmd)
            if result["ok"] and result.get("stdout"):
                return {
                    "ok": True,
                    "data": {
                        "source": cmd.split()[2] if cmd.startswith("tail") else "journalctl",
                        "logs": result["stdout"].split("\n"),
                        "line_count": len(result["stdout"].split("\n")),
                    },
                }
        # Try to find log files in common locations
        find_result = _run_command(client, "find ~/hermes /var/log/hermes -name '*.log' -type f 2>/dev/null | head -5")
        if find_result["ok"] and find_result.get("stdout"):
            return {"ok": False, "error": f"Command logs not found. Available: {find_result['stdout'].replace(chr(10), ', ')}"}
        return {"ok": False, "error": "Hermes command execution logs not found on the server."}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if client:
            client.close()


def fetch_all_logs(host: str, lines: int = 50) -> dict:
    """Fetch all Hermes logs combined (gateway + signal + commands)."""
    key_path = _get_ssh_key_path()
    username = _get_ssh_user()
    client = None
    try:
        client = _ssh_connect(host, key_path, username)
        results = {}
        # Gateway logs
        for cmd in [
            f"tail -{lines} ~/.hermes/logs/gateway.log 2>/dev/null",
            f"tail -{lines} /var/log/hermes/gateway.log 2>/dev/null",
            f"journalctl -u hermes-gateway --no-pager -n {lines} 2>/dev/null",
            f"tail -{lines} ~/hermes/gateway.log 2>/dev/null",
        ]:
            result = _run_command(client, cmd)
            if result.get("stdout"):
                results["gateway"] = result["stdout"].split("\n")
                break
        # Signal logs
        for cmd in [
            f"tail -{lines} ~/.hermes/logs/signal-cli.log 2>/dev/null",
            f"grep -i 'signal' ~/.hermes/logs/gateway.log 2>/dev/null | tail -{lines}",
            f"tail -{lines} /var/log/hermes/signal-cli.log 2>/dev/null",
            f"journalctl -u hermes-signal --no-pager -n {lines} 2>/dev/null",
            f"tail -{lines} ~/hermes/signal-cli.log 2>/dev/null",
        ]:
            result = _run_command(client, cmd)
            if result.get("stdout"):
                results["signal"] = result["stdout"].split("\n")
                break
        # Command logs
        for cmd in [
            f"tail -{lines} ~/.hermes/logs/agent.log 2>/dev/null",
            f"tail -{lines} ~/.hermes/logs/errors.log 2>/dev/null",
            f"tail -{lines} /var/log/hermes/commands.log 2>/dev/null",
            f"journalctl -u hermes-agent --no-pager -n {lines} 2>/dev/null",
            f"tail -{lines} ~/hermes/commands.log 2>/dev/null",
        ]:
            result = _run_command(client, cmd)
            if result.get("stdout"):
                results["commands"] = result["stdout"].split("\n")
                break
        # Service status
        svc = _run_command(client, "systemctl is-active hermes-agent 2>/dev/null || echo 'not_found'")
        results["service_status"] = svc.get("stdout", "unknown")
        
        if not results:
            return {"ok": False, "error": "No Hermes logs found on the server."}
        
        return {"ok": True, "data": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if client:
            client.close()


def fetch_disk_status(host: str) -> dict:
    """Fetch disk usage information from the Hermes server.
    
    Runs `df -h` and parses the output to provide structured disk data.
    Also fetches `du -sh` for key directories.
    """
    key_path = _get_ssh_key_path()
    username = _get_ssh_user()
    client = None
    try:
        client = _ssh_connect(host, key_path, username)
        
        # Get disk usage overview
        df_result = _run_command(client, "df -h --output=source,fstype,size,used,avail,pcent,target 2>/dev/null || df -h 2>/dev/null")
        if not df_result["ok"]:
            return {"ok": False, "error": f"Failed to get disk info: {df_result.get('stderr', 'unknown error')}"}
        
        # Parse the df output
        lines = df_result["stdout"].split("\n")
        header = lines[0] if lines else ""
        filesystems = []
        for line in lines[1:]:
            if line.strip():
                parts = line.split()
                if len(parts) >= 6:
                    fs = {
                        "filesystem": parts[0],
                        "type": parts[1] if len(parts) > 6 else "",
                        "size": parts[2] if len(parts) > 6 else parts[1],
                        "used": parts[3] if len(parts) > 6 else parts[2],
                        "avail": parts[4] if len(parts) > 6 else parts[3],
                        "use_pct": parts[5] if len(parts) > 6 else parts[4],
                        "mounted_on": parts[-1],
                    }
                    filesystems.append(fs)
        
        # Get total disk usage for key directories
        du_result = _run_command(client, "du -sh /var/log /home /tmp 2>/dev/null | sort -rh")
        dir_usage = []
        if du_result["ok"] and du_result.get("stdout"):
            for line in du_result["stdout"].split("\n"):
                if line.strip():
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        dir_usage.append({"path": parts[1], "size": parts[0]})
        
        # Get inode usage
        inode_result = _run_command(client, "df -i --output=source,iused,ipcent,target 2>/dev/null | tail -n +2 | head -5")
        inode_usage = []
        if inode_result["ok"] and inode_result.get("stdout"):
            for line in inode_result["stdout"].split("\n"):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        inode_usage.append({"filesystem": parts[0], "used": parts[1], "use_pct": parts[2], "mounted_on": parts[-1]})
        
        return {
            "ok": True,
            "data": {
                "filesystems": filesystems,
                "directory_usage": dir_usage,
                "inode_usage": inode_usage,
                "raw_df": df_result["stdout"],
            },
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if client:
            client.close()


def test_connection(host: str) -> dict:
    """Test SSH connection to the Hermes server.
    
    Returns a detailed diagnostic about what's working and what's not.
    """
    result = {
        "ok": False,
        "host": host,
        "checks": {},
    }
    
    # Check SSH key
    key_path = _get_ssh_key_path()
    result["checks"]["ssh_key_exists"] = os.path.exists(key_path)
    if result["checks"]["ssh_key_exists"]:
        st = os.stat(key_path)
        result["checks"]["ssh_key_permissions"] = oct(st.st_mode)
        # Check permissions are correct (should be 600)
        result["checks"]["ssh_key_permissions_ok"] = not (st.st_mode & 0o077)
    
    # Check username
    username = _get_ssh_user()
    result["checks"]["username"] = username
    
    # Try SSH connection
    client = None
    try:
        client = _ssh_connect(host, key_path, username)
        result["checks"]["ssh_connection"] = True
        
        # Check if Hermes Agent is installed
        svc = _run_command(client, "which hermes-agent 2>/dev/null && hermes-agent --version 2>/dev/null || systemctl list-units --type=service 2>/dev/null | grep hermes || echo 'hermes not found'")
        result["checks"]["hermes_agent_installed"] = svc.get("stdout", "").strip() != "hermes not found"
        result["checks"]["hermes_agent_version"] = svc.get("stdout", "").strip() if result["checks"]["hermes_agent_installed"] else "not found"
        
        # Check log directories
        log_dirs = _run_command(client, "ls -la ~/.hermes/logs/ 2>/dev/null || ls -la /var/log/hermes/ 2>/dev/null || ls -la ~/hermes/ 2>/dev/null || echo 'no_log_dirs'")
        result["checks"]["log_directories_exist"] = "no_log_dirs" not in (log_dirs.get("stdout", "") or "no_log_dirs")
        if result["checks"]["log_directories_exist"]:
            result["checks"]["log_files"] = [l.split()[-1] for l in log_dirs.get("stdout", "").split("\n") if l.strip() and not l.startswith(("total", "d"))][:10]

        # Check tmux sessions (Hermes runs via tmux, not systemd)
        tmux = _run_command(client, "tmux ls 2>/dev/null | tail -5")
        result["checks"]["tmux_sessions"] = tmux.get("stdout", "").strip() or "none"
        
        result["ok"] = True
    except FileNotFoundError as e:
        result["checks"]["ssh_key"] = str(e)
    except PermissionError as e:
        result["checks"]["ssh_auth"] = str(e)
    except (ConnectionError, TimeoutError) as e:
        result["checks"]["ssh_connection"] = str(e)
    except Exception as e:
        result["checks"]["unknown_error"] = str(e)
    finally:
        if client:
            client.close()
    
    return result
