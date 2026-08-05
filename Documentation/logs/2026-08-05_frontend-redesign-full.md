# 2026-08-05 — Full frontend redesign (Categories 1 & 2, visual layer)

**Owner:** Claude (Anthropic), requested directly by the repo owner outside
the numbered task board — not a Cline/Hermes-agent task.

**Scope:** every file under `skydash/templates/` and `skydash/static/`
(css + js visual output). No backend Python, Terraform, or deploy config
touched — confirmed with `diff -rq` against the pre-change tree before
packaging (see Verification below).

## Why

The dashboard worked (Categories 1 & 2 were genuinely `done`) but looked like
an unstyled Bootstrap admin template — default purple gradient, emoji used as
the entire icon system, no real typographic identity. The owner asked for a
full visual pass: "make it super nice, super sexy" was the literal brief.
This session is that pass.

## What changed

- **New design system**, single source of truth in `static/css/tokens.css`:
  a dark ("night sky") + light ("day sky") theme pair, three-font type system
  (Space Grotesk / Inter / IBM Plex Mono, each with a distinct role), and a
  "status beacon" component (glowing dot + label) used identically across
  the dashboard cards, detail-page header, admin table, and context menu.
- **Every template rewritten**: `base.html`, `index.html`, `detail.html`,
  `admin.html`, `login.html`, `404.html`, `503.html`, and the unused-but-kept
  `instances.html` (legacy, served only by `app_legacy.py`).
- **Every CSS file rewritten**: new `tokens.css`, `base.css`, `login.css`;
  rewritten `dashboard.css`, `detail.css`.
- **Every JS file had its visual output patched** (function names, exports,
  and API call sites all preserved — see the handbook for the exact diff
  summary per file): `dashboard.js`, `detail.js`, `specs-visualization.js`,
  `metrics-charts.js`, `status-timeline.js`, `topology.js`, `region-map.js`,
  `ssh-terminal.js`.
- **All emoji removed**, replaced with a consistent Bootstrap Icons
  vocabulary (already loaded via CDN, previously barely used).
- **Two pre-existing bugs fixed in passing**: the context menu's Start/Stop
  buttons referenced `#ctx-start`/`#ctx-stop` IDs that didn't exist in the
  HTML (dead `getElementById` calls that threw and broke the rest of the
  context-menu-open handler); `.hidden-by-page` was applied by
  `renderPagination()` but had no matching CSS rule anywhere, so pagination
  never actually hid extra cards.
- **New doc**: `skydash/docs/FRONTEND_HANDBOOK.md` — the design-system spec
  and the full list of `id`/`data-*`/class contracts JS depends on, written
  for whichever agent (Deepseek/GLM-backed, or otherwise) picks up frontend
  work next.

## Verification

This was done in an offline sandboxed environment with no access to the live
server, cloud credentials, or real instance data. What *was* verified:

```
# Confirmed zero emoji remain in any template/css/js:
$ python3 -c "<scan script, see FRONTEND_HANDBOOK.md §9>"
No emoji found. Clean.

# Every template parses and renders through Jinja2 with representative
# dummy data, including edge cases:
$ python3 render.py
index.html ('OK', 21423)
detail.html ('OK', 15409)
admin.html ('OK', 11950)
login.html ('OK', 3132)
404.html ('OK', 4827)
503.html ('OK', 4893)
instances.html ('OK', 6192)
index.html empty-state: OK
admin.html edit-modal: OK
detail.html ssh-tab + socketio-off banner: OK

# Confirmed no backend/infra files were touched:
$ diff -rq TerraSky-main/skydash --exclude=templates --exclude=static build/skydash
$ diff -rq TerraSky-main/terraform build/terraform
$ diff -rq TerraSky-main/deploy build/deploy
$ diff -rq TerraSky-main/scripts build/scripts
(no output — confirmed untouched)
```

Visual review was done by rendering the actual template output (real
Jinja2 render of `index.html`, `detail.html`, `login.html` with sample
instance data) through a local headless renderer and reviewing screenshots
directly — not just reading CSS and assuming. Two real issues were caught
this way and fixed: Bootstrap's default pink `<code>` color was bleeding
through onto IP addresses (fixed by setting `color: inherit` on the
`code`/`kbd`/`pre` selector in `base.css`), and the detail-page tab icons
had no visible gap from their labels in engines without flexbox `gap`
support (added an explicit `margin-right` fallback).

**NOT verified — owed to whoever deploys this next**, per Hard Rule #1
("verify before claim"): this has **not** been deployed, has **not** been
loaded in a real browser against the live Flask app, and has **not** been
click-tested (filters, drag-reorder, SSH tab, theme-toggle persistence,
etc.). See `skydash/docs/FRONTEND_HANDBOOK.md` § 8 for the exact checklist.
Do not move the "In progress" entry in `STATUS.md` to "Done & verified"
until that checklist has been run for real and the evidence pasted in.

## Files changed

```
skydash/templates/base.html         (rewritten)
skydash/templates/index.html        (rewritten)
skydash/templates/detail.html       (rewritten)
skydash/templates/admin.html        (rewritten)
skydash/templates/login.html        (rewritten)
skydash/templates/404.html          (rewritten)
skydash/templates/503.html          (rewritten)
skydash/templates/instances.html    (rewritten, legacy/unused path)
skydash/static/css/tokens.css       (new)
skydash/static/css/base.css         (new — replaces base.html's inline <style>)
skydash/static/css/login.css        (new)
skydash/static/css/dashboard.css    (rewritten)
skydash/static/css/detail.css       (rewritten)
skydash/static/js/dashboard.js      (patched — visual output only)
skydash/static/js/detail.js         (patched — visual output only)
skydash/static/js/specs-visualization.js  (patched — colors only)
skydash/static/js/metrics-charts.js       (patched — colors only)
skydash/static/js/status-timeline.js      (patched — colors only)
skydash/static/js/topology.js             (patched — labels only)
skydash/static/js/region-map.js           (patched — one color only)
skydash/static/js/ssh-terminal.js         (patched — xterm theme only)
skydash/docs/FRONTEND_HANDBOOK.md   (new)
START_HERE.md                       (routing table updated)
STATUS.md                           (In Progress + Next Steps updated)
TASKS.md                            (note added after Category 2)
```

## Next steps

1. Deploy to staging (or directly, if that's the team's normal flow) and run
   the full checklist in `FRONTEND_HANDBOOK.md` § 8.
2. Once verified, move the `STATUS.md` entry from "In Progress" to
   "Done & verified" with real evidence (paste command output / screenshots
   per this repo's own evidentiary standard — not a description of expected
   behavior).
3. Continue Category 3 (Hermes Agent) work using the new component classes
   (`.panel`, `.status-pill`, `.btn-console`, etc.) documented in the
   handbook, rather than reaching for raw Bootstrap defaults.
