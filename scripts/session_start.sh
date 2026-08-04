#!/bin/bash
# session_start.sh — resume-aware session orientation
# Usage: bash scripts/session_start.sh
echo "=== SkyDash session start: $(date -u '+%Y-%m-%d %H:%M UTC') ==="
echo ""

# 1. Resume check (rate-limit / mid-work recovery)
if [ -f /home/volodro/SESSION_IN_PROGRESS.md ]; then
  echo "⚠️  SESSION_IN_PROGRESS.md found — the last session was cut off mid-work."
  echo "    RESUME it FIRST. Read the file, continue its 'Current step'."
  echo "    -------------------------------------------------------------"
  head -50 /home/volodro/SESSION_IN_PROGRESS.md
  echo "    -------------------------------------------------------------"
else
  echo "✅ No in-progress checkpoint — you may start a new task."
fi
echo ""

# 2. Orientation pointers
echo "==> READ in this order:"
echo "    1) START_HERE.md            (fast orient + routing table, ~800 tokens)"
echo "    2) AGENT_ONBOARDING.md      (7 hard rules, quick)"
echo "    3) TASKS.md                 (pick first pending task)"
echo "    4) Documentation/SESSION_HANDOFF.md  (depth, once per session, ~2-3k)"
echo ""

# 3. Live status hint
echo "=> Run 'bash scripts/status.sh' for live state (reality check)."
echo ""
echo "Good work ahead! 🚀"
