# RuntimeLog — Category 1 UI/UX Dashboard (#4–10) complete
**Date:** 2026-08-04
**Owner:** Cline

## Original prompt
"Skip task setup secure admin password, move it to the backlog. Start working on
Cat #1 finish all task there. Update each milestone under this scope."

## Objective
Complete all pending Category 1 (UI/UX Dashboard) tasks (#4 region map, #5 tag filters,
#6 drag-drop, #7 CPU/RAM viz, #8 toasts, #9 quick-actions context menu, #10 pagination) and
perform the mandatory milestone doc-sync. Move "set secure admin password" to Backlog.

## Files modified
- `skydash/static/css/dashboard.css` (NEW) — toast stack, metric bars, map, tag dropdown,
  drag states, context menu, pagination styles.
- `skydash/static/js/dashboard.js` (NEW) — status polling, filters (multi-select tags +
  type/region), sort, drag-drop (Sortable+localStorage), actions, context menu,
  pagination/infinite scroll (IntersectionObserver), CPU/RAM load fetch, animated toasts.
- `skydash/static/js/region-map.js` (NEW) — Leaflet.js world map w/ provider-coloured markers.
- `skydash/templates/index.html` — full rewrite: map toggle, type/region/tag filters,
  CPU/RAM bars, sortable grid, context menu, pagination, static asset includes.
- `skydash/templates/base.html` — dashboard.css + Sortable.js includes; replaced single
  toast with `#toast-stack`; **fixed latent bug** `{{ super() }}` in base scripts block
  (base.html is the root template → super() is undefined → 500 on every error page).
- `skydash/app.py` — new `/api/load` endpoint (per-instance CPU/RAM from inventory +
  fleet-max for relative bars).
- `TASKS.md` — #4–10 → done w/ evidence; new **Backlog** section (admin password moved).
- `STATUS.md` — done table + next steps + known-limitations updated.
- `Documentation/SESSION_HANDOFF.md` — state + next path updated.

## Problems & solutions
1. **Port 8080 already bound** by the production `skydash.service` (systemd, pid 36366)
   holding OLD code in memory. → Verified changes on a throwaway instance on :8091
   (`from app import app; app.run(port=8091)`), leaving production untouched.
2. **`{{ super() }}` in base.html scripts block** raised `UndefinedError: there is no
   parent block called 'scripts'` (latent bug — production never hit it because it serves
   the pre-edit cached code). Removed the invalid `super()` call.
3. **`data-tags` HTML-escaping** — `tojson|forceescape` produces entity-escaped JSON in
   the attribute; `card.dataset.tags` auto-decodes entities, so `JSON.parse` works.
4. **CPU/RAM "real data" scope** — no live utilisation agents exist yet (that is Cat 3
   Hermes). `/api/load` intentionally returns real *inventory* specs (vCPU/RAM) relative to
   fleet max; documented that live utilisation comes later.

## Verification output (test instance :8091)
```
login=200
dash=200
/api/load → [{"cpu_pct":100,"cpu_vcpus":8.0,...,"slug":"alibaba-alibabapower"}, ... 7 rows]
/api/statuses → [{"can_manage":...,"slug":"alibaba-alibabapower",...}]
static/css/dashboard.css=200  js/dashboard.js=200  js/region-map.js=200
Rendered dashboard contains: map-toggle, region-map-wrap, tag-toggle, data-bar=cpu/ram,
context-menu, show-more, scroll-sentinel, data-ctx-action=start, toast-stack,
dashboard.js, region-map.js, dashboard.css, Sortable.min.js, data-tags= ✓ (all present)
```

## Deployment note
Changes are committed but NOT yet live on 74.248.232.219 (production runs the old in-memory
code). Next push to `main` → GitHub Actions deploy will ship them. Manual redeploy option:
`sudo systemctl restart skydash.service` on the server.

## Next steps
- Push to `main` to deploy via CI (or restart `skydash.service` on the server).
- Begin **Category 2 — UI/UX Detail pages** (#11 detail tabs, #12 progress loader, …).

## Remaining issues (echoed from prior logs)
- Azure/Oracle/Alibaba providers still need SDKs installed in the server venv
  (`azure-mgmt-compute`, `oci`, `alibabacloud-ecs20140526`) — blocks live status for 3 of 4
  clouds.
- Admin password hardening remains in the Backlog.
