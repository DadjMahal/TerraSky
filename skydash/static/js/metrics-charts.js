/* ============================================================================
   SkyDash — #18 Metrics charts for an instance (Chart.js)
   Draws CPU/RAM/disk bar charts from /api/metrics/<slug>. Live timeseries
   requires the monitoring agent (Cat 7); these charts reflect configured specs
   and (for Hermes) live disk usage.
   ============================================================================ */
(function () {
    "use strict";
    let cpuChart = null, diskChart = null;

    function num(v) { const m = /(\d+(?:\.\d+)?)/.exec(String(v)); return m ? parseFloat(m[1]) : 0; }

    async function render(slug) {
        const host = document.getElementById("metrics-host");
        if (!host) return;
        host.innerHTML = '<div class="text-muted">Loading…</div>';
        try {
            const res = await fetch(`/api/metrics/${slug}`, { cache: "no-store" });
            const m = await res.json();
            host.innerHTML = `
              <div class="row g-3">
                <div class="col-md-6 chart-card"><canvas id="cpuChart"></canvas></div>
                <div class="col-md-6 chart-card"><canvas id="diskChart"></canvas></div>
              </div>`;
            if (typeof Chart === "undefined") { host.innerHTML = '<div class="text-muted">Chart.js not loaded.</div>'; return; }
            if (cpuChart) cpuChart.destroy();
            if (diskChart) diskChart.destroy();
            cpuChart = new Chart(document.getElementById("cpuChart"), {
                type: "bar",
                data: { labels: ["CPU (vCPU)", "RAM (GB)"], datasets: [{ data: [num(m.cpu_vcpus), num(m.ram_gb)], backgroundColor: ["#0d6efd", "#198754"] }] },
                options: { plugins: { title: { display: true, text: "Configured capacity" } }, scales: { y: { beginAtZero: true } } },
            });
            // Disk usage (Hermes only) — pie of filesystems
            const disk = m.disk || {};
            const fsList = (disk.filesystems || []).filter(f => f && f.filesystem);
            diskChart = new Chart(document.getElementById("diskChart"), {
                type: disk.filesystems ? "bar" : "bar",
                data: { labels: fsList.map(f => f.mounted_on || f.filesystem), datasets: [{ label: "Use %", data: fsList.map(f => parseInt(f.use_pct) || 0), backgroundColor: "#fd7e14" }] },
                options: { plugins: { title: { display: true, text: m.disk ? "Live disk usage (Hermes)" : "Disk (GB)" } }, scales: { y: { beginAtZero: true, max: 100 } } },
            });
            if (m.disk_error) host.innerHTML += `<div class="small text-muted mt-2">Disk: ${m.disk_error}</div>`;
        } catch (e) { host.innerHTML = `<div class="text-danger">Failed: ${e.message}</div>`; }
    }

    window.SkyDashMetrics = { render };
})();
