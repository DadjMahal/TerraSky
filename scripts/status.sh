#!/bin/bash
# status.sh — one-shot live SkyDash state (reality check)
# Usage: bash scripts/status.sh   (run from /home/volodro)
set -e
echo "=== SkyDash live state: $(date -u '+%Y-%m-%d %H:%M UTC') ==="
echo ""

# 1. Service status
if command -v systemctl >/dev/null 2>&1; then
  SVC=$(systemctl is-active skydash.service 2>/dev/null || echo "unknown")
  echo "skydash.service   : $SVC"
else
  echo "skydash.service   : n/a (no systemctl on this host)"
fi

# 2. Listening ports (80 nginx, 8080 flask)
echo "--- listening ports ---"
ss -tlnp 2>/dev/null | grep -E ':80 |:8080 ' | awk '{print $4}' | sort -u || echo "  (none in :80/:8080)"

# 3. HTTP checks (via nginx on port 80)
echo "--- HTTP checks ---"
LOGIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost/login 2>/dev/null || echo "000")
echo "GET /login             : HTTP $LOGIN_CODE (expect 200)"
ROOT_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost/ 2>/dev/null || echo "000")
echo "GET /                  : HTTP $ROOT_CODE (expect 302 redirect to login)"
TITLE=$(curl -s --connect-timeout 5 http://localhost/login 2>/dev/null | grep -o '<title>[^<]*</title>' | head -1)
echo "Page title             : ${TITLE:-n/a} (expect SkyDash)"

# 4. Recent git
echo "--- recent git ---"
git -C /home/volodro log --oneline -3 2>/dev/null || true
echo ""
echo "Note: paste this output as evidence per the 7 Hard Rules."
