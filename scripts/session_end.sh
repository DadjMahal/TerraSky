#!/bin/bash
# session_end.sh — milestone doc-sync + commit + cleanup
# Usage: bash scripts/session_end.sh [commit_message]
# Ensures the knowledge base is current so a fresh session never reads stale context.
MSG="${1:-docs: session end - knowledge base sync}"

echo "=== SkyDash session end / doc-sync ==="
cd /home/volodro || exit 1

# 1. Show git status so you can confirm what will be committed
echo "--- uncommitted changes ---"
git status --short

# 2. Force update STATUS.md orient paragraphs if you have live evidence
echo ""
echo "NOTE: update STATUS.md / SESSION_HANDOFF.md / TASKS.md if they changed,"
echo "      then this will commit everything with the message below."

# 3. Commit all doc + code changes together
git add -A

# If SESSION_IN_PROGRESS.md exists and work is complete, remove it as a checkpoint
if [ -f SESSION_IN_PROGRESS.md ]; then
  echo ""
  echo "SESSION_IN_PROGRESS.md present. Remove it now? [y/N]"
  echo "(If the task is DONE and fully committed, answer y — it is then folded into the RuntimeLog.)"
  # keep it interactive only if a TTY; otherwise keep the checkpoint
  if [ -t 0 ]; then read -r ans; else ans=""; fi
  if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    git rm -f SESSION_IN_PROGRESS.md >/dev/null 2>&1 || rm -f SESSION_IN_PROGRESS.md
    echo "Removed SESSION_IN_PROGRESS.md (task complete)."
  fi
fi

git commit -m "$MSG" || echo "(nothing to commit or commit failed)"
echo ""
echo "Done. Push with:  git push origin main"
