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
    function tokenColor(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

    async function render(slug) {
        const host = document.getElementById("metrics-host");
        if (!host) return;
        host.innerHTML = '<div class="row g-3"><div class="col-md-6"><div class="skeleton" style="height:230px"></div></div><div class="col-md-6"><div class="skeleton" style="height:230px"></div></div></div>';
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
            const accent = tokenColor("--accent") || "#4FC8E8";
            const metricAlt = tokenColor("--metric-alt") || "#A78BFA";
            const metricAlt2 = tokenColor("--metric-alt-2") || "#E8A33D";
            const gridColor = tokenColor("--border") || "rgba(150,170,210,0.14)";
            const textColor = tokenColor("--text-muted") || "#93A2C2";
            Chart.defaults.color = textColor;
            Chart.defaults.font.family = "'Inter', sans-serif";
            const commonScales = { y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor } },
                                    x: { grid: { display: false }, ticks: { color: textColor } } };
            cpuChart = new Chart(document.getElementById("cpuChart"), {
                type: "bar",
                data: { labels: ["CPU (vCPU)", "RAM (GB)"], datasets: [{ data: [num(m.cpu_vcpus), num(m.ram_gb)], backgroundColor: [accent, metricAlt], borderRadius: 4 }] },
                options: { plugins: { title: { display: true, text: "Configured capacity", color: textColor }, legend: { display: false } }, scales: commonScales },
            });
            // Disk usage (Hermes only) — pie of filesystems
            const disk = m.disk || {};
            const fsList = (disk.filesystems || []).filter(f => f && f.filesystem);
            diskChart = new Chart(document.getElementById("diskChart"), {
                type: disk.filesystems ? "bar" : "bar",
                data: { labels: fsList.map(f => f.mounted_on || f.filesystem), datasets: [{ label: "Use %", data: fsList.map(f => parseInt(f.use_pct) || 0), backgroundColor: metricAlt2, borderRadius: 4 }] },
                options: { plugins: { title: { display: true, text: m.disk ? "Live disk usage (Hermes)" : "Disk (GB)", color: textColor }, legend: { display: false } },
                           scales: { y: { beginAtZero: true, max: 100, grid: { color: gridColor }, ticks: { color: textColor } }, x: { grid: { display: false }, ticks: { color: textColor } } } },
            });
            if (m.disk_error) host.innerHTML += `<div class="small text-faint mt-2">Disk: ${m.disk_error}</div>`;
        } catch (e) { host.innerHTML = `<div class="text-danger">Failed: ${e.message}</div>`; }
    }

    window.SkyDashMetrics = { render };
})();
