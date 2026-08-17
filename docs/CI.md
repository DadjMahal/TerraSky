# CI — SkyDash

> How to run the local test suite and how the GitHub Actions pipeline wires it up,
> plus a practical guide to adding new tests on both the frontend and the backend.
> Verified against the current repo state (`.github/workflows/ci.yml`,
> `tests/test_file_manager_js.js`, `tests/test_security_groups_js.js`,
> `skydash/tests/test_audit.py`, `jest.config.js`, `package.json`,
> `skydash/requirements-dev.txt`).

---

## 1. Running the full local test suite

The project has two independent test suites: a **backend** suite (Python + pytest,
living in `skydash/tests/`) and a **frontend** suite (JavaScript + Jest, living in
`tests/`). They are run separately.

### 1.1 Frontend (Jest)

```bash
cd /root/TerraSky
npx jest tests/ --ci
```

- Runs against the `tests/` directory (Jest is configured in `jest.config.js`).
- The Jest config uses the **jsdom** test environment:
  ```js
  module.exports = {
      testEnvironment: 'jsdom',
      testMatch: ['**/tests/**/*.test.js', '**/tests/**/*.spec.js', '**/tests/test_*.js'],
      testEnvironmentOptions: { url: 'http://localhost/' },
      verbose: true,
  };
  ```
- Tests are named `test_*.js` (e.g. `tests/test_file_manager_js.js`,
  `tests/test_security_groups_js.js`) and match the `**/tests/test_*.js` glob.
- `--ci` puts Jest in CI mode (clearer reporting; no interactive watch prompts).
- Dependencies come from `package.json` (`jest` and `jest-environment-jsdom` are
  devDependencies). Install them once with `npm ci` (or `npm install`).

### 1.2 Backend (pytest)

```bash
cd /root/TerraSky
python3 -m pytest skydash/tests/ -v
```

- Discovers every `test_*.py` file under `skydash/tests/` (e.g.
  `test_audit.py`, `test_agents.py`, `test_projects.py`, ...).
- `-v` prints one line per test (verbose).
- Prerequisite packages (pytest, pytest-cov, plus the production
  requirements) are declared in `skydash/requirements-dev.txt`:
  ```text
  -r requirements.txt
  pytest>=8.0
  pytest-cov>=5.0
  ```
  Install them locally with:
  ```bash
  cd /root/TerraSky
  python3 -m pip install -r skydash/requirements-dev.txt
  ```


---

## 2. GitHub Actions pipeline (`.github/workflows/ci.yml`)

The workflow triggers on push to `main` and on pull requests targeting `main`:

```yaml
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
```

It defines **two independent jobs** that run in parallel: `frontend-tests` and
`backend-tests`. Both run on `ubuntu-latest`.

### 2.1 Job: `frontend-tests`

| Step | Action / command | Notes |
|------|------------------|-------|
| 1 | `actions/checkout@v4` | Checks out the repo. |
| 2 | `actions/setup-node@v4` with `node-version: '18'`, `cache: 'npm'` | Installs Node 18 and enables the npm dependency cache (`package-lock.json`). |
| 3 | `npm ci` | Clean, reproducible install from `package-lock.json` (fails if the lockfile is out of sync with `package.json`). |
| 4 | `npx jest tests/test_file_manager_js.js tests/test_security_groups_js.js --ci` | Runs the two frontend test files in CI mode. |

### 2.2 Job: `backend-tests`

| Step | Action / command | Notes |
|------|------------------|-------|
| 1 | `actions/checkout@v4` | Checks out the repo. |
| 2 | `actions/setup-python@v5` with `python-version: '3.10'`, `cache: 'pip'`, `cache-dependency-path: 'skydash/requirements-dev.txt'` | Installs Python 3.10 and caches pip deps keyed on the dev-requirements file. |
| 3 | `pip install -r skydash/requirements-dev.txt` | Installs production + test dependencies. |
| 4 | `python3 -m pytest skydash/tests/ --maxfail=1 -v` | Runs the whole backend suite, stopping after the first failure. |

### 2.3 Caching

- **npm:** `actions/setup-node@v4` with `cache: 'npm'` restores/caches the npm
  cache and relies on `package-lock.json` being committed.
- **pip:** `actions/setup-python@v5` with `cache: 'pip'` and
  `cache-dependency-path: 'skydash/requirements-dev.txt'` caches installed wheels.
  The cache key is derived from the dev-requirements file, so any change to that
  file invalidates the cache.

### 2.4 Notes / divergence between CI and local

- The local "full" frontend command runs `npx jest tests/ --ci` (the whole test
  directory); CI explicitly lists the two test files. New frontend tests live
  under `tests/` and match the `**/tests/test_*.js` glob, so they are found
  locally by `npx jest tests/ --ci` and can be added to the CI file list.
- CI uses `--maxfail=1` on pytest (fail fast); local runs usually do not, so a
  local run reports every failing test in one pass.

---

## 3. How to add a test

### 3.1 Python (backend) — new file in `skydash/tests/`

Add a new file such as `skydash/tests/test_<thing>.py`. It is auto-discovered by
`pytest` (any `test_*.py` under `skydash/tests/`).

**Bootstrap pattern (`sys.path.insert`).** Each test file pushes the `skydash/`
package directory onto `sys.path` so it can import the module under test directly.
From `skydash/tests/test_audit.py`:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import audit   # module under test, imported after the path fix
```

This is the same pattern used across all backend tests (every `test_*.py` in
`skydash/tests/` performs this `sys.path.insert` before importing its target).

**Isolation fixtures.** Prefer pytest fixtures (`tmp_path`, `monkeypatch`) so tests
never write to real state. `test_audit.py` redirects the audit log directory to a
temp dir and resets the in-memory sequence cache for every test:

```python
@pytest.fixture(autouse=True)
def _isolated_audit_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "AUDIT_DIR", str(tmp_path))
    monkeypatch.setattr(audit, "_SEQ_CACHE", {})
    yield tmp_path
```

**Style conventions in this repo:**
- One test case per function named `test_<what>_<happens>` (no classes needed).
- Flatten the imports (e.g. `from datetime import date`) or import inside the
  function (e.g. `test_audit.py` uses `from datetime import datetime` locally).
- Use plain `assert` statements with `unittest.mock`/`monkeypatch` for stubbing.
- Run it with: `python3 -m pytest skydash/tests/test_<thing>.py -v`.

### 3.2 Frontend (JS) — new file `tests/test_<thing>_js.js`

Frontend modules are plain IIFEs in `skydash/static/js/` (no import/export), so the
tests load them by **reading the file and `eval`-ing it inside a jsdom window**.
Add a sibling test file under `tests/`, e.g.
`tests/test_<thing>_js.js` (matches the `**/tests/test_*.js` glob).

**`loadModule` pattern.** Copy the shape from
`tests/test_file_manager_js.js` or `tests/test_security_groups_js.js`:

```js
const fs = require('fs');
const path = require('path');
const SRC_PATH = path.resolve(__dirname, '../skydash/static/js/<thing>.js');
let src;
try { src = fs.readFileSync(SRC_PATH, 'utf8'); } catch (e) { src = null; }

function loadModule(opts = {}) {
  delete window.SkyDashThing;            // clear the previous exposure
  window.SKYDASH_SLUG = opts.slug !== undefined ? opts.slug : 'my-instance';
  window.SKYDASH_INST = opts.inst || {};
  // set whatever DOM hosts / globals the IIFE reads at load time ...
  global.fetch.mockReset();
  global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({ status: 'ok', data: {} }) });
  expect(src).not.toBeNull();
  eval(src);                             // run the IIFE in the jsdom window
  if (opts.dispatchDOMContentLoaded !== false) {
    document.dispatchEvent(new Event('DOMContentLoaded'));
  }
  return window.SkyDashThing;
}
```

Call `loadModule()` fresh in each test (via `beforeEach`) so tests start from a
clean state — the IIFEs intentionally re-evaluate per case.

### 3.3 Three pitfalls to know

1. **`bubbles: true`.** Bootstrap tab events are listened for at the **document**
   level (see the `shown.bs.tab` handlers in `file-manager.js` /
   `security-groups.js`). To trigger one, dispatch a synthetic event on a child
   element and set `{ bubbles: true }` so it propagates up to the document
   listener:

   ```js
   const target = document.createElement('div');
   target.getAttribute = (attr) => (attr === 'href' ? '#tab-files' : null);
   document.body.appendChild(target);
   target.dispatchEvent(new CustomEvent('shown.bs.tab', { bubbles: true }));
   ```

   Without `bubbles: true` the document-level listener never fires.

2. **Listener guards.** The modules guard against re-registration / premature
   execution, and the tests must respect that.
   - `file-manager.js` sets an `_initialized` flag only once
     `DOMContentLoaded` has fired AND the `fm-listing` host exists; `init()` is
     only called when the `shown.bs.tab` handler sees `#tab-files` **and**
     `_initialized` is true. That is why `loadModule` dispatches
     `DOMContentLoaded` by default — pass `{ dispatchDOMContentLoaded: false }`
     to skip it when you only want to call `init()` / `navigate()` yourself.
   - `security-groups.js` registers its tab listener only once per window via a
     `window.__SKYDASH_SG_TAB_LISTENER__` flag, and it calls `init()` at load
     time **unless** `document.readyState === 'loading'`. Its `loadModule`
     stubs `document.readyState` with `Object.defineProperty(...)` to control
     which path is taken. Mirror this when testing similar guarded modules.

3. **`flush()`.** Renders happen asynchronously in `fetch(...).then(...)`
   callbacks, and tests must wait for those microtasks to settle before asserting
   on `innerHTML`. The repo uses a tiny `flush()` helper that yields to the event
   loop:

   ```js
   const flush = () => new Promise(r => setTimeout(r, 30));
   // ...
   window.SkyDashThing.navigate('/');
   await flush();
   expect(listing()).toContain('file.txt');
   ```

   `security-groups.js` uses `setTimeout(resolve, 0)`; `file-manager.js` uses
   `setTimeout(resolve, 30)`. Use the same `await flush()` after any action that
   triggers a fetch/render, or your assertions will run before the DOM updates.
   The only assertions that may run synchronously are those checking that a
   fetch/mock *was called* (the call itself is synchronous), as in the
   `shown.bs.tab` test.
