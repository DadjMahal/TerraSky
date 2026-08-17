# Test Coverage — SkyDash

> Current (as of this writing) backend + frontend test-coverage snapshot of the
> repo: which modules have a dedicated test file, which do not, how to run every
> suite, and how to add new tests. Verified against the live repo state
> (`for f in skydash/*.py; do b=...; [ -f skydash/tests/test_$b.py ] || echo "$b"`
> and the equivalent for `skydash/static/js/*.js` vs `tests/test_*_js.js`),
> `skydash/tests/` (30 test files), `tests/` (4 Jest files), `jest.config.js`,
> `package.json`, `skydash/requirements-dev.txt`, `.coveragerc`, and
> `.github/workflows/ci.yml`.

---

## 1. Coverage snapshot (summary)

| Suite | Modules | Dedicated test file | No dedicated test |
|-------|---------|--------------------:|------------------:|
| Backend (`skydash/*.py`) | 32 | 23 (72%) | 9 (28%) |
| Frontend (`skydash/static/js/*.js`) | 13 | 4 (31%) | 9 (69%) |

What this table counts is a **dedicated sibling test file per module**
(`skydash/tests/test_<name>.py` on the backend, `tests/test_<name>_js.js` on the
frontend). A module without a sibling file may still receive *some* coverage via
the broader integration test files listed in §2.2 / §3.3, but it has no
first-class test of its own.

---

## 2. Backend — module-by-module (`skydash/*.py`)

### 2.1 Modules with a dedicated test (23)

| Module | Test file |
|--------|-----------|
| `agent_registry.py` | `skydash/tests/test_agent_registry.py` |
| `audit.py` | `skydash/tests/test_audit.py` |
| `config_store.py` | `skydash/tests/test_config_store.py` |
| `crypto.py` | `skydash/tests/test_crypto.py` |
| `dependencies.py` | `skydash/tests/test_dependencies.py` |
| `drift.py` | `skydash/tests/test_drift.py` |
| `health.py` | `skydash/tests/test_health.py` |
| `import_engine.py` | `skydash/tests/test_import_engine.py` |
| `instance_format.py` | `skydash/tests/test_instance_format.py` |
| `instance_specs.py` | `skydash/tests/test_instance_specs.py` |
| `inventory.py` | `skydash/tests/test_inventory.py` |
| `openapi.py` | `skydash/tests/test_openapi.py` |
| `policy.py` | `skydash/tests/test_policy.py` |
| `projects.py` | `skydash/tests/test_projects.py` |
| `rbac.py` | `skydash/tests/test_rbac.py` |
| `reports.py` | `skydash/tests/test_reports.py` |
| `scheduler.py` | `skydash/tests/test_scheduler.py` |
| `security_checklist.py` | `skydash/tests/test_security_checklist.py` |
| `sftp_client.py` | `skydash/tests/test_sftp_client.py` |
| `state_reader.py` | `skydash/tests/test_state_reader.py` |
| `status_history.py` | `skydash/tests/test_status_history.py` |
| `tfplan.py` | `skydash/tests/test_tfplan.py` |
| `workers.py` | `skydash/tests/test_workers.py` |

### 2.2 Modules still lacking a dedicated test (9)

These are the modules reported by the verification loop:

```bash
for f in skydash/*.py; do b=$(basename "$f" .py); [ -f "skydash/tests/test_$b.py" ] || echo "$b"; done
# agent_protocol
# app
# auth
# cli
# db
# hermes_agent
# models
# prometheus_metrics
# ssh_bridge
```

| Module | Notes |
|--------|-------|
| `agent_protocol.py` | No test file at all. |
| `app.py` | No `test_app.py`. Some routes/behaviour are exercised indirectly by `test_lifecycle.py`, `test_governance.py`, `test_monitoring.py`, `test_agents.py` (which `import app`-adjacent helpers), but there is no dedicated app/route test. |
| `auth.py` | No `test_auth.py`. |
| `cli.py` | No `test_cli.py`. |
| `db.py` | No `test_db.py`. |
| `hermes_agent.py` | No `test_hermes_agent.py`. |
| `models.py` | No `test_models.py`; `Instance` is used across many tests but has no dedicated dataclass test. |
| `prometheus_metrics.py` | No `test_prometheus_metrics.py` (some path covered by `test_monitoring.py`). |
| `ssh_bridge.py` | No `test_ssh_bridge.py`. |

### 2.3 Additional backend test files (not 1:1 with a top-level module)

`skydash/tests/` currently has **30** `test_*.py` files. Besides the 23 in §2.1,
the following 7 target subpackages / cross-cutting behaviour:

| Test file | Covers |
|-----------|--------|
| `test_agents.py` | `skydash/plugins` (agent plugin machinery) |
| `test_deployments.py` | `skydash/deployments/approvals`, `deployments/applications` |
| `test_governance.py` | `audit`, `policy`, `rbac`, `crypto` (integration-style) |
| `test_lifecycle.py` | `drift`, `dependencies`, `scheduler`, `import_engine`, `status_history` |
| `test_monitoring.py` | `inventory`, `health` |
| `test_providers_contract.py` | `providers/base`, `providers/registry` (`all_providers`) |
| `test_security_groups.py` | `providers/security_groups` |

> ⚠️ Note on the assumed gap list: an earlier snapshot listed
> `agent_registry`, `config_store`, `openapi`, `reports`, `scheduler`, and
> `workers` as having no tests. Those six **now have** test files (all currently
> untracked in git, i.e. added since the last commit), which is why they appear in
> §2.1 rather than §2.2.

---

## 3. Frontend — module-by-module (`skydash/static/js/*.js`)

Jest test files live in `tests/` and use the `test_<module>_js.js` naming, with
`-` in the module name replaced by `_` (e.g. `file-manager.js` →
`tests/test_file_manager_js.js`). There are currently **4** Jest files covering
**4 of 13** JS modules.

### 3.1 JS modules with a dedicated test (4)

| Module | Test file |
|--------|-----------|
| `file-manager.js` | `tests/test_file_manager_js.js` |
| `menu.js` | `tests/test_menu_js.js` |
| `notifications.js` | `tests/test_notifications_js.js` |
| `security-groups.js` | `tests/test_security_groups_js.js` |

### 3.2 JS modules still lacking a dedicated test (9)

```bash
for f in skydash/static/js/*.js; do b=$(basename "$f" .js | tr - _); [ -f "tests/test_${b}_js.js" ] || echo "$b"; done
# csrf-header
# dashboard
# detail
# metrics-charts
# region-map
# specs-visualization
# ssh-terminal
# status-timeline
# topology
```

| Module | Notes |
|--------|-------|
| `csrf-header.js` | No test. |
| `dashboard.js` | No test. |
| `detail.js` | No test. |
| `metrics-charts.js` | No test. |
| `region-map.js` | No test. |
| `specs-visualization.js` | No test. |
| `ssh-terminal.js` | No test. |
| `status-timeline.js` | No test. |
| `topology.js` | No test. |

### 3.3 CI runs only a subset

`.github/workflows/ci.yml` executes only
`test_file_manager_js.js test_security_groups_js.js`. Locally, `npx jest tests/ --ci`
discovers all four; `menu.js` and `notifications.js` tests are not yet wired into CI.

---

## 4. Exact commands to run the suites

### 4.1 Backend (pytest)

```bash
cd /root/TerraSky
python3 -m pytest skydash/tests/ -v                      # whole backend suite, verbose
python3 -m pytest skydash/tests/test_<name>.py -v        # a single test file
```

Optional line-coverage report (needs `pytest-cov`, which is declared in
`skydash/requirements-dev.txt`; `coverage` is *not* installed in this sandbox):

```bash
cd /root/TerraSky
python3 -m pytest skydash/tests/ --cov=skydash --cov-report=term-missing
```

`skydash/requirements-dev.txt` installs the prerequisite packages:

```text
-r requirements.txt
pytest>=8.0
pytest-cov>=5.0
```

### 4.2 Frontend (Jest)

```bash
cd /root/TerraSky
npx jest tests/ --ci                                    # all frontend tests (jsdom)
npx jest tests/test_<module>_js.js --ci                 # a single Jest file
```

Jest config (`jest.config.js`): `testEnvironment: 'jsdom'`, and
`testMatch: ['**/tests/**/*.test.js', '**/tests/**/*.spec.js', '**/tests/test_*.js']`.

---

## 5. How to add a new test file

### 5.1 Python (backend) — `skydash/tests/test_<name>.py`

Add a file `skydash/tests/test_<name>.py` for module `skydash/<name>.py`. pytest
auto-discovers it (any `test_*.py` under `skydash/tests/`). Bootstrap the import
path exactly like the existing tests:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import <name>   # module under test, imported after the path fix
```

- One test case per function, named `test_<what>_<happens>` (plain functions, no
  classes needed).
- Prefer pytest fixtures (`tmp_path`, `monkeypatch`) so tests never touch real
  state — see the `_isolated_audit_dir` autouse fixture in `test_audit.py`.
- Use plain `assert` statements with `unittest.mock` / `monkeypatch` for stubbing.
- Run it: `python3 -m pytest skydash/tests/test_<name>.py -v`.
- Full suite: `python3 -m pytest skydash/tests/ -v`.

### 5.2 JavaScript (frontend) — `tests/test_<module>_js.js`

Frontend modules are plain IIFEs in `skydash/static/js/` (no import/export), so
tests load them by **reading the file and `eval`-ing it inside the jsdom window**.
Copy the `loadModule` shape from `tests/test_file_manager_js.js` (or
`test_security_groups_js.js`): resolve `skydash/static/js/<module>.js`, clear the
prior `window.SkyDash*` global, stub `global.fetch`, `eval(src)`, dispatch
`DOMContentLoaded` (unless disabled), and return the exposed global.

```js
const fs = require('fs');
const path = require('path');
const SRC_PATH = path.resolve(__dirname, '../skydash/static/js/<module>.js');
let src;
try { src = fs.readFileSync(SRC_PATH, 'utf8'); } catch (e) { src = null; }

function loadModule(opts = {}) {
  delete window.SkyDashThing;
  window.SKYDASH_SLUG = opts.slug !== undefined ? opts.slug : 'my-instance';
  global.fetch.mockReset();
  global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
  expect(src).not.toBeNull();
  eval(src);
  if (opts.dispatchDOMContentLoaded !== false) {
    document.dispatchEvent(new Event('DOMContentLoaded'));
  }
  return window.SkyDashThing;
}
```

Name it `tests/test_<module>_js.js` (`-` → `_`, e.g. `region-map.js` →
`tests/test_region_map_js.js`) so it matches the `**/tests/test_*.js` glob, and
run it with `npx jest tests/test_<module>_js.js --ci`.

**Three pitfalls to remember** (from CI.md §3.3):
1. **`bubbles: true`** — Bootstrap tab events are listened at the document level;
   dispatch synthetic `shown.bs.tab` events with `{ bubbles: true }`.
2. **Listener guards** — modules guard against re-registration
   (`_initialized`, `window.__SKYDASH_SG_TAB_LISTENER__`); stub `document.readyState`
   where needed and re-evaluate `loadModule()` fresh per test via `beforeEach`.
3. **`await flush()`** — renders happen in `fetch(...).then(...)` microtasks;
   `const flush = () => new Promise(r => setTimeout(r, 30));` before asserting on
   `innerHTML`.

Full frontend suite: `npx jest tests/ --ci`.

---

## 6. Static analysis (pyflakes)

Run with:

```bash
cd /root/TerraSky
python3 -m pyflakes skydash/*.py 2>&1 | head -40
```

(Install once if missing: `python3 -m pip install --user pyflakes`.)

**Result:** 17 findings across 8 files (after one fix, see §6.2). pyflakes exits
with code 1 when findings are present, so an exit code of 1 here is expected.

### 6.1 Findings grouped by file

**`skydash/agent_registry.py`** (1)
- `agent_registry.py:12:1: 'dataclasses.field' imported but unused`

**`skydash/app.py`** (8)
- `app.py:18:1: 'flask_limiter.Limiter' imported but unused`
- `app.py:19:1: 'flask_limiter.util.get_remote_address' imported but unused`
- `app.py:24:1: 'auth.auth_bp' imported but unused`
- `app.py:28:1: 'projects' imported but unused`
- `app.py:493:5: 'deployments.approvals.create as create_approval' imported but unused`
- `app.py:706:5: 'projects.get_project' imported but unused`
- `app.py:864:5: 'flask_socketio.disconnect' imported but unused`
- `app.py:868:1: local variable 'e' is assigned to but never used`

**`skydash/auth.py`** (2 — after the fix below)
- `auth.py:11:1: 'datetime.timedelta' imported but unused` (a local
  `from datetime import timedelta` inside `login()` shadows it)
- `auth.py:72:17: redefinition of unused 'timedelta' from line 11`

**`skydash/dependencies.py`** (1)
- `dependencies.py:35:5: local variable 'by_slug' is assigned to but never used`

**`skydash/drift.py`** (1)
- `drift.py:12:1: 'models.STATUS_STOPPED' imported but unused`

**`skydash/hermes_agent.py`** (2)
- `hermes_agent.py:21:1: 'stat as stat_module' imported but unused`
- `hermes_agent.py:323:9: local variable 'header' is assigned to but never used`

**`skydash/import_engine.py`** (1)
- `import_engine.py:17:1: 'typing.Any' imported but unused`

**`skydash/state_reader.py`** (1)
- `state_reader.py:377:9: local variable 'state' is assigned to but never used`

### 6.2 One fix applied

Per repo policy, only a single 100%-obviously-safe unused-import fix was applied:

- **`skydash/auth.py` — removed `import os` (previously line 11).** Auth.py was
  read in full; `os` was never referenced anywhere in the file (no `os.` usage),
  and no other module imports `os` from `auth` — 100% dead import. Verified:
  `python3 -m pyflakes skydash/auth.py` no longer reports the `os` finding, and
  `python3 -m compileall -q skydash/auth.py` passes.

The remaining findings above are left in place: several (e.g. the `app.py`
unused imports) require reading large files end-to-end to prove safety, and the
`auth.py` `timedelta` pair involves a deliberate local re-import pattern, so they
are reported here rather than changed.