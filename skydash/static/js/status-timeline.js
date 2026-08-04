/* ============================================================================
   SkyDash — #15 Status change timeline
   Renders a horizontal timeline from /api/status-history/<slug>.
   ============================================================================ */
(function () {
    "use strict";

    const COLOR = {
        running: "#198754", stopped: "#dc3545", starting: "#0dcaf0",
        stopping: "#ffc107", error: "#dc3545", unknown: "#6c757d",
    };

    async function render(slug) {
        const host = document.getElementById("timeline-host");
        if (!host) return;
        host.innerHTML = '<div class="text-muted">Loading…</div>';
        try {
            const res = await fetch(`/api/status-history/${slug}`, { cache: "no-store" });
            const data = await res.json();
            if (!Array.isArray(data) || !data.length) {
                host.innerHTML = '<div class="text-muted small">No status history yet. History is recorded as live statuses are polled.</div>';
                return;
            }
            const rows = data.slice(-12);
            host.innerHTML = `<div class="timeline"><div class="tl-line"></div><div class="tl-track">` +
                rows.map(e => {
                    const t = new Date((e.ts || 0) * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    const c = COLOR[e.status] || COLOR.unknown;
                    return `<div class="tl-event"><div class="dot" style="background:${c}"></div><div class="tl-time">${t}</div><div class="small">${e.status}</div></div>`;
                }).join("") + `</div></div>`;
        } catch (e) { host.innerHTML = `<div class="text-danger">Failed: ${e.message}</div>`; }
    }

    window.SkyDashTimeline = { render };
})();
