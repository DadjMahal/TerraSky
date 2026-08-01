# Execution Log: Auth, Hermes Agent & Disk Status

## Date and Time
- **Started**: 2026-07-30 21:00 UTC
- **Finished**: 2026-07-30 21:55 UTC

## User Prompt
> "1. Make an authorization and login page. Super secure. Only authorized user
> should have access to read and execute data. 2. Extend functionality of Hermes
> server. I have Hermes Agent installed and want to receive all logs via button
> retrieve Hermes logs. Logs should be about: Hermes Gateway worklog, Signal-Cli
> worklog, all commands executed on the server. 3. Create information data about
> server's current disk status (how loaded, GB used)."

## Actions Performed

### 1. Authentication System
- Created `auth.py` — Flask Blueprint with:
  - `login_required` decorator protecting ALL routes
  - Password hashing via `werkzeug.security.generate_password_hash` / `check_password_hash`
  - Login route (GET/POST) with session management (1-hour timeout)
  - Logout route (clears session)
  - `get_current_user()` helper
  - Admin password read from `SKYDASH_ADMIN_PASSWORD` env var (default: "admin")
- Created `templates/login.html` — Bootstrap 5 login page with:
  - Dark gradient background, branded card design
  - Username/password form with input group icons
  - Error and flash message display
  - Responsive, mobile-friendly layout
- Updated `app.py` — initialized auth blueprint, added `@login_required` to ALL routes
- Updated `templates/index.html` — added logout button + user info to navbar
- Updated `templates/detail.html` — added logout button + user info to navbar

### 2. Hermes Agent SSH Log Retrieval
- Installed `paramiko` SSH library in venv
- Created `hermes_agent.py` — SSH-based log retrieval module with:
  - `fetch_gateway_logs(host)` — Hermes Gateway worklog (tries `/var/log/hermes/gateway.log`, `journalctl -u hermes-gateway`, `~/hermes/gateway.log`)
  - `fetch_signal_logs(host)` — Signal-Cli worklog (tries multiple log locations)
  - `fetch_command_logs(host)` — Command execution logs (tries multiple locations + `find` fallback)
  - `fetch_all_logs(host)` — Combined view of all log types + service status
  - `fetch_disk_status(host)` — `df -h` parsing + `du -sh` for directories + inode usage
  - `test_connection(host)` — Full SSH diagnostics (key exists, key permissions, connection, agent installed, log directories)
  - SSH key-based auth (RSA + Ed25519), lazy paramiko import, descriptive error messages
- Added endpoints to `app.py`:
  - `GET /hermes/<slug>/logs/<type>` — fetch logs by type (gateway, signal, commands, all)
  - `GET /hermes/<slug>/disk` — disk status
  - `GET /hermes/<slug>/test` — SSH connection test with diagnostics
  - All use **live IP** from the AWS API (not stale TF state IP)
- Updated `templates/detail.html` — added Hermes Agent card (only for Hermes instance):
  - Test Connection button
  - Gateway Logs, Signal Logs, Command Logs, All Logs buttons
  - Disk Status button
  - Log display area with colored lines (error/warning/info)
  - Disk usage table with color-coded rows (red >90%, yellow >75%)

### 3. Disk Status Monitoring
- Implemented as part of `hermes_agent.py` (`fetch_disk_status`)
- Parses `df -h` output into structured data: filesystem, size, used, avail, use%, mounted
- Fetches directory sizes via `du -sh /var/log /home /tmp`
- Fetches inode usage via `df -i`
- Color-coded table in UI: rows turn red when disk usage >90%, yellow >75%

### 4. Bug Fixes
- Fixed Hermes endpoints using stale TF state IP → now use live IP via `provider.get_instance_details()`
- Applied to all 3 Hermes endpoints (logs, disk, test)

## Errors
- `paramiko` not installed → installed via `pip install paramiko` in venv
- Hermes endpoints used stale TF state IP (`3.75.96.99`) instead of live IP (`63.179.97.116`) → fixed by calling `provider.get_instance_details()` before using IP
- No SSH key at `~/.ssh/id_rsa` → user needs to configure `HERMES_SSH_KEY_PATH` in `.env`

## Result
- **Login page**: loads at `/login`, redirects unauthenticated users from all routes ✓
- **Auth works**: login with `admin:admin` → session created → dashboard accessible ✓
- **Logout**: clears session → redirects to login ✓
- **Hermes detail page**: shows Hermes Agent section (Gateway Logs, Signal Logs, Command Logs, All Logs, Disk Status, Test Connection buttons) ✓
- **Hermes test connection**: shows correct live IP `63.179.97.116` ✓
- **SSH key**: not configured yet — user needs to set `HERMES_SSH_KEY_PATH` in `.env`
- **All 14 routes registered**: `/login`, `/logout`, `/`, `/instance/<slug>`, `/api/statuses`, `/api/status/<slug>`, `/instance/<slug>/<action>`, `/logs/<slug>`, `/logs/<slug>/scan`, `/hermes/<slug>/logs/<type>`, `/hermes/<slug>/disk`, `/hermes/<slug>/test`, `/refresh`

## User Action Required
1. **Set admin password**: Add `SKYDASH_ADMIN_PASSWORD=your_secure_password` to `~/terraform/.env`
2. **Configure SSH for Hermes Agent**: Generate SSH key, add public key to Hermes server's `~/.ssh/authorized_keys`, and set in `.env`:
   ```
   HERMES_SSH_KEY_PATH=/home/volodro/.ssh/id_rsa
   HERMES_SSH_USER=ubuntu
   HERMES_SSH_HOST=63.179.97.116
   ```
3. After configuring, restart Flask: `pkill -f '[a]pp.py' && nohup /tmp/start_skydash.sh > flask.log 2>&1 &`