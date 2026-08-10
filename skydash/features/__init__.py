"""Agent-managed server feature contracts (§16, §20-24) — scaffolding only.

Each module documents the *agent-side command* that a future SkyDash agent
(``docs/ai-agent-development.md`` §96-98) would run on the managed server to
implement the feature. The platform API foundation (routes + permission model)
is defined here; the actual execution requires a deployed agent on the target
host, so execution itself is **BLOCKED / not-yet-wired** in this environment.

Status convention: ``FEATURE_STATUS = "scaffold"``. Flip to ``"wired"`` when a
route calls into the module and an agent implementation exists.
"""