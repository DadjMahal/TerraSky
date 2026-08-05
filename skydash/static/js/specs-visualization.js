/* ============================================================================
   SkyDash — #13 Hardware specs visualization (animated SVG gauges)
   Renders CPU / RAM / Disk as circular gauges from /api/metrics/<slug>.
   ============================================================================ */
(function () {
    "use strict";

    function polar(cx, cy, r, deg) {
        const rad = (deg - 90) * Math.PI / 180;
        return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
    }
    function arcPath(cx, cy, r, startDeg, endDeg) {
        const [sx, sy] = polar(cx, cy, r, endDeg);
        const [ex, ey] = polar(cx, cy, r, startDeg);
        const large = endDeg - startDeg <= 180 ? 0 : 1;
        return `M ${sx} ${sy} A ${r} ${r} 0 ${large} 0 ${ex} ${ey}`;
    }
    function gauge(label, value, max, unit, color) {
        const r = 52, cx = 60, cy = 60;
        const pct = max > 0 ? Math.min(1, value / max) : 0;
        const circ = 2 * Math.PI * r;
        const dash = circ * 0.75; // 270° track
        const fill = dash * pct;
        return `
        <div class="spec-gauge col-4">
          <svg viewBox="0 0 120 120">
            <path class="gauge-track" d="${arcPath(cx, cy, r, 135, 405)}" fill="none" stroke-width="10"/>
            <path class="gauge-fill" d="${arcPath(cx, cy, r, 135, 135 + 270 * pct)}" fill="none" style="stroke:${color}" stroke-width="10" stroke-linecap="round"
                  stroke-dasharray="${fill} ${circ}" />
            <text class="gauge-value" x="60" y="64" text-anchor="middle">${value}${unit}</text>
            <text class="gauge-label" x="60" y="100" text-anchor="middle">${label}</text>
          </svg>
        </div>`;
    }
    function num(v) { const m = /(\d+(?:\.\d+)?)/.exec(String(v)); return m ? parseFloat(m[1]) : 0; }

    async function render(slug) {
        const host = document.getElementById("specs-host");
        if (!host) return;
        host.innerHTML = '<div class="text-muted">Loading&hellip;</div>';
        try {
            const res = await fetch(`/api/metrics/${slug}`, { cache: "no-store" });
            const m = await res.json();
            const cpu = m.cpu_vcpus ?? 0, ram = m.ram_gb ?? 0, disk = m.disk_gb ?? 0;
            host.innerHTML = `<div class="row g-3">
                ${gauge("CPU", cpu, 8, "", "var(--accent)")}
                ${gauge("RAM", ram, 16, "GB", "var(--metric-alt)")}
                ${gauge("Disk", disk, 100, "GB", "var(--metric-alt-2)")}
            </div>
            <div class="small text-faint mt-2">Bars show configured capacity vs an 8 vCPU / 16 GB / 100 GB reference.
            Live utilisation comes with the monitoring agent (Cat 7).</div>`;
        } catch (e) { host.innerHTML = `<div class="text-danger">Failed: ${e.message}</div>`; }
    }

    window.SkyDashSpecs = { render };
})();
