# SkyDash AI Agent Development

> **Created:** 2026-08-10 · Source: §132-135, §96-98 + existing `hermes_agent.py`.

## 1. Purpose

This platform must be **AI-agent friendly** (§143): agents (like Cline) discover resources and take actions through the same API the web UI uses. No UI-only paths.

## 2. Existing Agent Tangents

- `skydash/hermes_agent.py` — SSH-based log retrieval + disk/process monitoring of the Hermes server (paramiko). It is a server-side connector, not an agent protocol.
- `docs/ai-agent-development.md` (this file) formalizes the §132-135 protocol for future agent integrations.

## 3. Agent Task Protocol (§134)

```text
Agent (Cline/other) ──POST /api/v1/tasks ──> Platform
   { task_type, resource_id, params, intent, project_scope }

Platform ──> agent:
   job resource with status (queued/running/success/failed/requires_approval)
   streaming logs via WebSocket (§131)
   result payload + audit trail (§37)
```

## 4. Action Capabilities an Agent Can Invoke

| Capability | Endpoint(s) | Permission |
|---|---|---|
| Read inventory | GET /api/v1/servers · statuses · metrics | server.read |
| Start/Stop/Reboot | POST /api/v1/servers/{id}/actions | server.start / server.stop |
| Deploy | POST /api/v1/deployments | deployment.create |
| Terraform plan/apply | POST /api/v1/terraform/{workspace} | terraform.plan / terraform.apply |
| Command exec | POST /api/v1/servers/{id}/exec | server.exec (approval for prod) |
| File transfer | PUT /api/v1/servers/{id}/files | server.files |

## 5. AI Agent Rules (§133, §135 Safety)

1. **No destructive action without explicit approval** — destroy/terminate/delete require `approval: admin` (prod) or type-resource-name (UI).
2. Always explain the reasoning in the task `intent` field.
3. Every action is rate limited (§76) and audited (§37).
4. Sandboxed command execution — worker isolation §74, allowlist §75, timeout, output caps, emergency stop.
5. Agents never receive secrets — secrets are referenced by ID only (§29-30); credential values stay in the backend.

## 6. Agent Enrollment & Communication (§96-98)

- Server agents: short-lived single-use enrollment tokens → register → token invalidated.
- Agent → platform preferred (agent connects out, avoids inbound open ports).
- Agent permissions: project-scoped read/write.

## 7. Build Plan

| Iteration | Deliverable |
|---|---|
| 9 (this) | `/api/v1` auth (API tokens §94), agent task protocol, plugins §72-73, worker isolation §74, exec security §75, agent enrollment §96 |
| Ready today | API surface for statuses/start/stop already exists (unversioned) — will be aliased under `/api/v1/` |

## 8. Definition of Done for an Agent Integration

- Agent can list servers via API (GET).
- Agent can start/stop with audit record.
- No action bypasses authorization/approval.
- No secret value is ever returned to the agent.