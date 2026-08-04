# 📋 WORKFLOW — SkyDash (single rules/workflow reference)

> Orientation lives in `START_HERE.md`; rules in `AGENT_ONBOARDING.md`; the task
> board is `TASKS.md`. This is the ONE workflow reference.

## 1. Session Startup (read in this order)

1. `START_HERE.md` (orient; ~800 tokens).
2. If `SESSION_IN_PROGRESS.md` exists → **resume it first** (cut-off mid-work).
3. `AGENT_ONBOARDING.md` (7 hard rules).
4. `TASKS.md` (pick the first pending task) — unless resuming.
5. Run `START_HERE.md`'s Reality-check commands; **paste output** before claiming anything works.

## 2. The Hard Rules (non-negotiable)

**Verify before claim · No fake logs · Usage validation · Audit-first ·
Document before code · Leave cleaner · Milestone doc-sync.**
Full text in `AGENT_ONBOARDING.md`.

## 3. Milestone doc-sync (MANDATORY at every milestone)

Claim one task: set `in_progress` + your name in `TASKS.md`. Do the work. Verify
with a real command; paste the output BEFORE claiming it works. Then sync the
knowledge base at every milestone — update **ALL** of:
- `TASKS.md` (status + one-line Result + Evidence)
- `STATUS.md`
- `START_HERE.md` (orient) — only if task-level facts changed
- `Documentation/SESSION_HANDOFF.md` (depth)

Write a RuntimeLog (`Documentation/logs/YYYY-MM-DD-<task>.md`) recording the
original prompt, objective, files changed, problems & solutions, verification
output, next steps. Then git commit (`type(scope): brief`).

> ⚠️ **Milestone doc-sync is MANDATORY at every milestone even when the whole
> session is NOT finished.** Do NOT defer doc updates to session end.
> If a turn is cut off (e.g. rate-limit), you MUST still have committed: the
> RuntimeLog, `STATUS.md`/`START_HERE.md` orient, `SESSION_HANDOFF.md` depth,
> `TASKS.md` board status, and (for multi-step work) a `SESSION_IN_PROGRESS.md`
> checkpoint. The next session resumes from accurate, current context.

## 4. Rate-limit-safe resumability (IMPORTANT)

Multi-step work MUST be recoverable if a session is cut off mid-work:
- At the start of multi-step work, write **`SESSION_IN_PROGRESS.md`** at repo root:
  goal, idempotent checklist, current step, last command output, and
  *"if resuming: do X next"*.
- Update it before AND after every atomic step (mark `← IN PROGRESS`, then `[x]`).
- Commit a WIP checkpoint after each step: `git add -A && git commit -m "WIP(<step>): ..."`.
- Keep steps idempotent (a half-applied step must be safe to re-run).
- On clean completion, fold the scratchpad into the final RuntimeLog and
  `git rm SESSION_IN_PROGRESS.md`.

## 5. Multi-Agent Rules (future, if multiple agents)

- **Naming:** assign an owner name; set it in `TASKS.md` Owner + RuntimeLog.
- **Lock:** never edit a task line another agent set `in_progress`.
- **Token budget:** docs-only 500–1.5k; code+docs 2–5k; full feature 5–10k.
- **Merge conflict:** pull first; second agent commits WIP and re-syncs.
- One agent per subsystem folder at a time for multi-file changes.

## 6. RuntimeLog convention

`Documentation/logs/YYYY-MM-DD_<short-task>.md`, concise (≤40–70 lines):
original prompt, objective, files modified, problems & solutions, verification
output, next steps. Echo the prior log's "remaining issues" for continuity.
(Per original `PROMPT_LOGGING.md` requirements: date/time, user prompt, actions,
errors, result.)

## 7. Verification commands

```bash
scripts/status.sh                                   # live server state (reality check)
systemctl status skydash.service --no-pager | head   # service health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/login   # expect 200
python3 -m py_compile skydash/app.py                 # syntax check
cd /home/volodro && git status                       # tree state
```

## 8. Git workflow

Smaller commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `perf:`, `refactor:`, `style:`.
Paste the verification output ("HTTP 200" / "BUILD/TEST PASS") in the message or RuntimeLog.
WIP commits (`WIP(<step>): ...`) are valid checkpoints for long tasks.

## 9. Documentation rules

Keep docs short, accurate, useful. Update stale files immediately. **Never delete
docs — quarantine** to `_archive_*` with an index entry. Document only what helps
future work. This document is the master workflow reference; when in doubt, follow
`START_HERE.md` routing + `AGENT_ONBOARDING.md` rules first.
