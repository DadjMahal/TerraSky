# Execution Log: CI/CD Full Fix - Site Online + Robust Deployment

## Date and Time
- **Started**: 2026-08-04
- **Finished**: 2026-08-04

## User Prompt
> "Bro can u fix the gap in our CI/CD workflow. So now first of all on the destination
> site everything is down (no site available)... i would like you to finish setting up our
> workflow between you -> github -> destination server -> UPDATED SKYDASH & TERAFORM"

## Root Cause (Multiple Layers)

### Layer 1: nginx not configured as reverse proxy
Flask ran on port 8080, but nginx (port 80) was NOT configured to proxy to it. Public site
showed the stale nginx default "Welcome to nginx!" page.

### Layer 2: 'script:' input silently ignored (the BIG one)
The "Configure nginx" and "Deploy and restart" steps used `uses: webfactory/ssh-agent` with
a `script:` input. **webfactory/ssh-agent has NO 'script' input** - it only sets up the SSH
agent. The entire script blocks were SILENTLY IGNORED, so nginx was never configured and
Flask never started, yet CI reported "success" (steps were no-ops).

### Layer 3: pkill self-match bug
`pkill -f "app.py"` matched its OWN command line (the literal "app.py" appears in the shell
args), killing the SSH session -> step always failed. Fixed with `[a]pp.py` bracket trick.

### Layer 4: backgrounding hung SSH
Inline `setid nohup ... &` kept SSH stdout open -> step hung/timed out.

## Actions Performed

1. **Diagnosed** via port sweep (80=nginx default, 8080=blocked, 22=open) and headers.
2. **Gained SSH access** with existing `~/.ssh/github_deploy` key (deploy target is
   `power-vm-2`, a separate server from my sandbox `free-vm`).
3. **Created** `deploy/nginx/skydash.conf` (port 80 -> 127.0.0.1:8080, security headers,
   WS support, long timeouts). Fixed `.gitignore` to whitelist `deploy/`.
4. **Rewrote** the two broken steps as proper `run:` blocks using direct SSH
   (`ssh -i ~/.ssh/deploy_key volodro@SERVER_IP ...`).
5. **Added** "External public health check" step - runs from GitHub runner (public network,
   same as a browser) to catch routing/front-proxy issues.
6. **Converted to systemd**: `skydash.service` (Restart=always, EnvironmentFile=.env).
   Deploy now uses `systemctl restart` - robust, no background jobs/hangs, survives
   disconnects, auto-restarts on failure.

## Errors Resolved
- nginx config rsync failed (remote dir missing) -> added `mkdir -p`
- `deploy/` git-ignored -> whitelisted
- webfactory/ssh-agent `script:` no-op -> proper `run:` SSH blocks
- `pkill -f "app.py"` self-match -> `[a]pp.py`
- inline backgrounding hang -> systemd service

## Result (VERIFIED)
- ✅ CI/CD run **77c0f1f: SUCCESS** (all steps pass)
- ✅ Public site live: **http://74.248.232.219/**
- ✅ Title: **"Login &mdash; SkyDash"** - the actual app, not nginx default
- ✅ `/login` -> HTTP 200; `/` -> HTTP 302 (redirect to auth login = correct)
- ✅ `skydash.service` active; Flask on 8080; nginx on 80
- ✅ Full chain: **GitHub push -> rsync -> configure nginx -> systemd restart -> health check**

## Next Steps
1. Log in and verify theme toggle + dashboard UI (Tasks #1-3)
2. Proceed to remaining UI/UX tasks (#4+)
