# FRONTEND_HANDBOOK.md

**Audience:** any AI coding agent (Deepseek, GLM, Cline, or other) picking up frontend
work on SkyDash after the Category 1/2 UI/UX redesign. Read this **before** touching
any file under `skydash/templates/` or `skydash/static/`.

**Status:** the redesign described here is implemented and verified by local
rendering (Jinja2 render tests + screenshot review). It has **not** been deployed
or click-tested against the live server at 74.248.232.219 — that verification is
still owed by whoever deploys it next. See "What is NOT verified" at the bottom.

---

## 1. What changed, in one paragraph

Every template, every CSS file, and the visual-output parts of every JS file
under `skydash/` were rewritten. The old look (Bootstrap defaults, purple
gradient background, emoji used as icons) is gone. The new system is a dark
(and light) "instrument panel" theme with one color/spacing/type source of
truth (`tokens.css`), a consistent Bootstrap Icons vocabulary instead of
emoji, and a "status beacon" component used everywhere an instance's state is
shown. **No backend Python, Terraform, or deploy script was touched** — this
was a frontend-only pass.

## 2. Read this first: the golden rule

> **Never hardcode a color, font, spacing value, or radius in a template or a
> component CSS file.** Every visual value comes from a CSS custom property
> defined in `tokens.css`. If you need a new color, add a token there — don't
> write a hex code somewhere else. This is what makes it possible to keep dark
> and light theme in sync, and it's the #1 thing that will silently rot the
> design if skipped.

Second rule, just as important:

> **Every `id`, `data-*` attribute, and structural class listed in Section 5
> is load-bearing.** JavaScript queries these directly. Renaming or removing
> one without updating the matching JS breaks a feature at runtime with no
> build-time warning, because this project has no build step or type checker
> in front of the templates.

## 3. File map

```
skydash/static/css/
  tokens.css      — SOURCE OF TRUTH. Every color/font/spacing/radius token.
                     Dark theme = :root and [data-theme="dark"].
                     Light theme = [data-theme="light"].
  base.css        — resets, typography, navbar, buttons, forms, status pills,
                     tables, tabs, modals, alerts. Loaded on every page.
  dashboard.css   — index.html only: card grid, filters, region map, context
                     menu, toasts, pagination.
  detail.css      — detail.html only: tabs, action-progress loader, log
                     viewer, SSH terminal chrome, gauges, topology, timeline.
  login.css       — login.html only (login.html does NOT extend base.html,
                     so it does not get base.css — keep login.css in sync
                     with tokens.css by hand if you change shared values).

skydash/templates/
  base.html       — shell every other page extends. Nav, flash messages,
                     toast stack, loader modal, theme-toggle script.
  index.html      — dashboard / card grid.
  detail.html     — per-instance tabbed view.
  admin.html      — settings / profile / instance management.
  login.html      — standalone (own <html>, own head).
  404.html/503.html — error pages, use the .state-panel component.
  instances.html  — LEGACY. Served only by app_legacy.py, which is not the
                     live app (app.py is — see STATUS.md). Kept in sync for
                     consistency but is not a priority.

skydash/static/js/  — unchanged in structure/function names. Only visual
                       output (class names, inline colors, emoji) was edited.
                       See Section 6 for exactly what changed per file.
```

## 4. The design system, briefly

**Concept:** SkyDash's own name ("sky") plus its subject (multi-cloud
instrument panel for real servers) — dark, atmospheric "night sky" theme by
default, with a "day sky" light theme as a genuine second theme, not an
afterthought. Signature element: the **status beacon** — a glowing dot +
label used identically on the dashboard cards, the detail page header, the
admin table, and the context menu, so an instance's state reads the same way
everywhere.

**Type system** — three families, three jobs, don't blur them:
| Family | Role | Used for |
|---|---|---|
| `Space Grotesk` (`--font-display`) | brand & headings, used sparingly | nav brand, page titles, card names |
| `Inter` (`--font-body`) | interface chrome | buttons, labels, paragraphs, form fields |
| `IBM Plex Mono` (`--font-mono`) | every technical value | IPs, instance IDs, kv-labels, log lines, terraform addresses |

If you add UI copy, ask which of the three roles it is and use that family —
don't introduce a fourth font.

**Color** — everything is a token. The ones you'll touch most:
| Token | Purpose |
|---|---|
| `--void` / `--surface` / `--surface-2` / `--surface-3` | page bg → card → nested surface → hover/active |
| `--text` / `--text-muted` / `--text-faint` | primary / secondary / tertiary text |
| `--accent` / `--accent-strong` / `--accent-soft` | primary interactive color (sky-cyan) |
| `--status-running` / `-stopped` / `-starting` / `-stopping` / `-error` / `-unknown` (+ `-soft`, `-border` variants) | beacon/status colors |
| `--provider-aws` / `-azure` / `-oracle` / `-alibaba` | fixed brand colors, also used by the Leaflet map markers — keep these three places in sync if you ever change one |
| `--metric-alt`, `--metric-alt-2` | secondary gauge/chart colors (RAM, Disk) so they don't collide with status colors |

Both themes define the **same token names** with different values. Never
write theme-conditional CSS (`[data-theme="light"] .my-class {...}`) if you
can instead just use the token — that's the entire point of the token layer.

## 5. Contracts JavaScript depends on — do not rename without updating the JS

This is the list that matters most for "don't break things." Each row is an
`id`/`data-*`/structural class that a JS file queries by exact string.

| Selector | File(s) that query it | If you must change it |
|---|---|---|
| `#cards`, `.card-col`, `data-slug`, `data-name`, `data-provider`, `data-status`, `data-region`, `data-type`, `data-tags` | `dashboard.js` | Update every `querySelector`/`dataset` reference in the filter/sort/poll functions |
| `[data-status-badge]`, `#status-badge` (detail page) | `dashboard.js`, `detail.js` | Update `badgeHtml()` / `setBadge()` |
| `[data-ip="public"]` / `[data-ip="private"]` | `dashboard.js`, `detail.js` | Update the poll function that writes live IPs in |
| `[data-bar="cpu"]` / `[data-bar="ram"]`, `[data-bar-label="cpu"]` / `[data-bar-label="ram"]` | `dashboard.js` | Update `fetchLoad()` |
| `[data-actions]`, `button[data-action="start"/"stop"/"refresh"]` | `dashboard.js`, `detail.js` | Update the action click handlers |
| `.card-header-drag` | `dashboard.js` (`Sortable.create(..., handle: ...)`) | Update the `handle:` selector to match |
| `#context-menu`, `#ctx-title`, `#ctx-start`, `#ctx-stop`, `#ctx-detail`, `#ctx-logs`, `button[data-ctx-action]` | `dashboard.js` | All six IDs are read directly by `getElementById` — see the bug note below |
| `#region-map-wrap`, `#region-map`, `#map-error`, `#map-toggle` | `dashboard.js`, `region-map.js` | Update `SkyDashRegionMap.init()` |
| `#scroll-sentinel`, `#pagination-controls`, `#load-count`, `#show-more`, `.hidden`, `.hidden-by-page` | `dashboard.js` | Both hide classes must exist in CSS — see bug note below |
| `#toast-stack`, `.skydash-toast`, `.toast-progress`, `.btn-close-toast` | `dashboard.js` (`showToast`), `detail.js` (fallback `showToast`) | Keep both in sync — detail.js's own toast only fires when `dashboard.js` isn't loaded on that page |
| Tab `href`s: `#tab-overview`, `#tab-hardware`, `#tab-network`, `#tab-actions`, `#tab-timeline`, `#tab-logs`, `#tab-metrics`, `#tab-domains`, `#tab-ssh` | `detail.js` (`location.hash` sync via `shown.bs.tab`) | Changing a hash breaks deep-linking to that tab |
| `#specs-host`, `#topology-host`, `#timeline-host`, `#metrics-host`, `#ssh-host` | `specs-visualization.js`, `topology.js`, `status-timeline.js`, `metrics-charts.js`, `ssh-terminal.js` | These are just mount points — safe to restyle, don't rename |
| `#action-progress`, `.stage[data-stage]`, `.stage .dot`, `.stage.active`, `.stage.done` | `detail.js` (`showProgress`/`setStage`) | Structural, generated entirely by JS |
| `.log-viewer`, `.lv-line`, `.lv-error`/`.lv-warning`/`.lv-info` | `detail.js` (`renderLogs`) | |
| `.domain-row` | `detail.js` | |
| `window.__SKYDASH_INSTANCES__` (index.html), `window.SKYDASH_SLUG` / `window.SKYDASH_INST` (detail.html) | `dashboard.js`, `region-map.js`, `detail.js` and its sibling modules | Set inline in the template `{% block scripts %}`, before the JS files load |

**Two pre-existing bugs were fixed as part of this pass** (mentioned so
nobody "fixes" them back by reverting the HTML):
1. The context menu's Start/Stop buttons now have `id="ctx-start"` /
   `id="ctx-stop"` in `index.html`. Previously `dashboard.js` called
   `getElementById("ctx-start")` on an element that didn't exist, which threw
   and silently broke the rest of the context-menu-open handler (the Details/
   Logs links never got their `href` updated).
2. `.hidden-by-page` (used by `renderPagination()` to hide cards beyond the
   current page) had no matching CSS rule anywhere, so pagination didn't
   visually hide anything. It's now defined in `dashboard.css` alongside
   `.hidden`.

## 6. What changed inside each JS file (so a diff makes sense)

All files kept their function names, exported globals (`window.SkyDash*`),
and API call sites untouched. Only rendering/markup/color changed:

- **`dashboard.js`** — `STATUS_META` + `badgeHtml()` now emit the beacon
  markup (`<span class="status-pill status-X"><span class="beacon-dot">…`)
  instead of Bootstrap `bg-*` badges. `showToast()` rebuilt around the new
  toast component. Two `populateSelect()` calls lost their emoji prefixes.
  `Sortable.create` handle selector updated to `.card-header-drag`.
- **`detail.js`** — same `STATUS_META`/badge treatment as above (kept in
  sync intentionally — if you change one, change both). Its own fallback
  `showToast()` (used because `dashboard.js` isn't loaded on the detail
  page) rebuilt to match. Minor emoji/unicode cleanup in toast text and the
  domain-delete button.
- **`specs-visualization.js`** — gauge stroke colors switched from hardcoded
  hex to `var(--accent)` / `var(--metric-alt)` / `var(--metric-alt-2)`,
  passed via inline `style="stroke:…"` (SVG presentation *attributes* don't
  resolve `var()`, but an inline `style` does — don't switch this back to a
  bare `stroke="…"` attribute).
- **`metrics-charts.js`** — Chart.js colors resolved at render time via
  `getComputedStyle(document.documentElement).getPropertyValue('--token')`.
  Canvas doesn't understand CSS variables at all (unlike SVG), so this
  resolve-to-literal step is required, not optional. Charts pick up
  whichever theme is active *at render time*; they don't live-update if the
  user flips the theme toggle while already on the Metrics tab.
- **`status-timeline.js`** — `COLOR` map now points at `var(--status-*)`
  tokens instead of hardcoded Bootstrap colors.
- **`topology.js`** — dropped the two emoji in node labels (icon fonts don't
  render reliably inside SVG `<text>`) in favor of plain uppercase labels;
  added `.node-primary` for the instance node.
- **`region-map.js`** — provider marker colors unchanged (still the literal
  hex values, matching `--provider-*` tokens — see the sync note in Section
  4). The click-to-highlight box-shadow now uses `var(--accent)`.
- **`ssh-terminal.js`** — xterm.js `theme` object recolored from stock
  black/neon-green to the palette (`background:#0A0F1C`, phosphor-mint
  foreground, cyan cursor).

## 7. Extending the UI: rules for new features

1. **New instance status?** Add a token pair in `tokens.css`
   (`--status-foo` + `--status-foo-soft` + `--status-foo-border`, both
   themes), a rule in `base.css` (`.status-foo { … }`, following the
   existing five), and an entry in **both** `STATUS_META` objects
   (`dashboard.js` and `detail.js`). All three or it'll render as `unknown`.
2. **New provider?** Add `--provider-foo` to `tokens.css`, a `.strip-foo` /
   `.provider-foo` pair to `base.css`/`dashboard.css`, an entry in
   `PROVIDER_COLOR` in `region-map.js`, and a `<option>` in the dashboard
   filter select in `index.html`.
3. **New icon?** Bootstrap Icons only (`bi-*`, already loaded via CDN in
   `base.html`). Never add an emoji character to a template or a JS
   template-string. If you're unsure an icon exists, check
   https://icons.getbootstrap.com rather than guessing a class name.
4. **New page?** Extend `base.html`, not a fresh `<html>` doc — unless it's
   genuinely pre-auth like `login.html`, in which case link `tokens.css` and
   write a small page-specific stylesheet the way `login.css` does, and keep
   its hardcoded values in sync with `tokens.css` by hand (it can't inherit
   `base.css` since it doesn't extend `base.html`).
5. **New JS-rendered color** (chart, SVG, canvas)? Prefer resolving a CSS
   token over hardcoding a hex, using whichever technique matches the
   surface: inline `style="fill:var(--x)"` works for SVG, `getComputedStyle`
   resolution is required for Canvas, direct hex is only acceptable for
   things that must look identical in both themes on purpose (e.g. the SSH
   terminal, which stays dark regardless of site theme by design).
6. **Before you ship a template change**, check Section 5. If you touched
   anything in that table, grep the corresponding JS file for the old string
   to make sure nothing still references it.

## 8. What is NOT verified (owed to whoever deploys this)

This redesign was built and reviewed **offline** — rendered via Jinja2 with
representative dummy data and screenshotted with a local headless renderer,
not run against the live Flask app (no cloud credentials / real instance
data were available in that environment). Before calling this "done" in
`STATUS.md`, the next session should, per `WORKFLOW.md` § "Verify before
claim":
- Deploy to staging or the live host and load `/`, `/instance/<slug>`,
  `/admin`, `/login` in an actual browser.
- Click-test: filters, search, sort, tag dropdown, drag-to-reorder, region
  map toggle, right-click context menu, start/stop actions, all detail-page
  tabs (especially the Hermes SSH tab, which depends on Flask-SocketIO being
  enabled), theme toggle persistence across reload.
- Confirm `/static/css/tokens.css`, `base.css`, `login.css` are actually
  served (they're new files — nginx/static config doesn't need changes
  since Flask serves everything under `skydash/static/` already, but this
  wasn't confirmed against the real deployment).
- Run axe/Lighthouse or similar if accessibility scoring matters for this
  project; focus-visible states and color contrast were done by hand, not
  automated-tested.

## 9. Quick verification commands

```bash
# No emoji anywhere in templates/js/css
python3 -c "
import re, glob
p = re.compile('[\U0001F300-\U0001FAFF\U00002600-\U000027BF]')
for f in glob.glob('skydash/templates/**/*.html', recursive=True) + glob.glob('skydash/static/js/*.js') + glob.glob('skydash/static/css/*.css'):
    for i, l in enumerate(open(f, encoding='utf-8'), 1):
        if p.search(l): print(f, i, l.strip())
"

# Every template renders without a Jinja2 error (adjust context as needed —
# see the render test this handbook's own PR used, in the session log)
python3 -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('skydash/templates'))
for name in ['base.html','index.html','detail.html','admin.html','login.html','404.html','503.html','instances.html']:
    env.get_template(name)  # raises TemplateSyntaxError if broken
print('all templates parse OK')
"
```

---

*This document replaces the old task_planning docs (`01_ux_shutek_dashboard.md`,
`02_ux_detail_pages.md`) as the reference for frontend conventions going
forward — those two remain useful for historical context on what Cline
originally built, but this handbook reflects the current state after the
redesign. See `START_HERE.md` for where this fits in the routing table.*
