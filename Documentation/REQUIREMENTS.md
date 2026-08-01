# Requirements for Cline (CLI Assistant)

## General Behavior Rules

1. Always start by reading the documentation inside the `Documentation/` directory.

2. Before modifying code or configuration, make sure the current project structure is fully understood by reading `README.md`.

3. If any task requires user intervention (API keys, cloud authentication, configuration, etc.):

   - Clearly explain the required steps.
   - Mark them with:

     ```
     [USER ACTION REQUIRED]
     ```

   - Wait for user confirmation before continuing.

4. Every code modification should contain brief comments explaining:

   - What was changed.
   - Why it was changed.

5. After completing every task:

   - Update `README.md`
   - Reflect new functionality.
   - Document architecture changes.
   - Describe fixed issues.

6. Always verify functionality after making changes.

Examples:

- Restart Flask.
- Check logs.
- Perform test requests.
- Verify application startup.

---

## Language Requirements

Documentation, logs, comments, and internal notes:

**English**

Communication with the user:

**Ukrainian**

This means:

| Content | Language |
|----------|----------|
| Documentation | English |
| Logs | English |
| Code comments | English |
| Internal notes | English |
| User messages | Ukrainian |

---

## Logging Requirements

Logging rules are defined in:

```
PROMPT_LOGGING.md
```

Requirements:

- Store logs inside:

```
Documentation/logs/
```

Each log must include:

- Date and time
- User prompt
- Actions performed
- Errors (if any)
- Result

---

## Communication with User

- Always respond in Ukrainian.
- If an error occurs:
  - Report it immediately.
  - Explain the reason.
  - Suggest a solution.
- Never perform destructive operations without explicit user confirmation.

Examples:

- deleting files
- modifying cloud resources
- changing infrastructure
- modifying `.env`

---

## Constraints

Cline must NOT:

- Modify `.env` without permission.
- Execute commands that may cause:
  - data loss
  - downtime
  - service interruption
- Assume uncertain information.

If anything is unclear:

**Ask the user first.**
