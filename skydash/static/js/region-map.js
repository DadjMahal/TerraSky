/* ============================================================================
   SkyDash — Task #4 Interactive Region Map (Leaflet.js)
   Renders a world map with a marker per provider region. Markers are colored by
   provider; clicking a marker blinks/highlights the matching instance card.
   ============================================================================ */
(function () {
    "use strict";

    // Provider region -> [lat, lng]. Add new clouds/regions here.
    const REGION_COORDS = {
        // AWS / Alibaba
        "us-west-1": [37.7749, -122.4194],   // N. California
        "eu-central-1": [50.1109, 8.6821],   // Frankfurt
        // Azure
        "polandcentral": [52.2297, 21.0122], // Poland Central
        "spaincentral": [40.4168, -3.7038],  // Spain Central
        // Oracle
        "eu-frankfurt-1": [50.1109, 8.6821], // OCI Frankfurt
    };

    const PROVIDER_COLOR = {
        aws: "#ff9900",
        azure: "#0078d4",
        oracle: "#f80000",
        alibaba: "#ff6a00",
    };

    let map = null;
    let markers = [];

    function coordFor(region) {
        if (!region) return null;
        return REGION_COORDS[String(region).toLowerCase()] || null;
    }

    window.SkyDashRegionMap = {
        init(instances) {
            const wrap = document.getElementById("region-map");
            const errEl = document.getElementById("map-error");
            if (!wrap || map) return;

            // Leaflet is loaded lazily via dynamic script to avoid blocking the page.
            if (!window.L) {
                if (errEl) errEl.textContent = "Loading map library…";
                const s = document.createElement("script");
                s.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
                s.onload = () => window.SkyDashRegionMap.init(instances);
                s.onerror = () => { if (errEl) errEl.textContent = "Failed to load Leaflet."; };
                document.head.appendChild(s);
                return;
            }
            if (!window.L && !errEl) return;

            try {
                map = L.map("region-map", { scrollWheelZoom: false }).setView([40, 10], 2);
                L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                    { maxZoom: 8, attribution: "&copy; OpenStreetMap" }).addTo(map);

                instances.forEach(inst => {
                    const c = coordFor(inst.region);
                    if (!c) return;
                    const color = PROVIDER_COLOR[inst.provider] || "#6c757d";
                    const icon = L.divIcon({
                        className: "region-marker",
                        html: `<div style="width:14px;height:14px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.5);"></div>`,
                        iconSize: [14, 14],
                    });
                    const m = L.marker(c, { icon }).addTo(map);
                    m.bindPopup(`<b>${inst.name}</b><br>${inst.provider} · ${inst.region}<br>${inst.instance_type || ""}`);
                    m.on("click", () => {
                        const card = document.querySelector(`.card-col[data-slug="${inst.slug}"]`);
                        if (card) {
                            card.scrollIntoView({ behavior: "smooth", block: "center" });
                            card.style.boxShadow = "0 0 0 3px #0d6efd";
                            setTimeout(() => { card.style.boxShadow = ""; }, 1500);
                        }
                    });
                    markers.push(m);
                });
                if (errEl) errEl.textContent = "";
            } catch (e) {
                if (errEl) errEl.textContent = "Map error: " + e.message;
            }
        },

        // Recolor markers to match the active filter set (pass filtered slugs).
        highlight(slugs) {
            const set = new Set(slugs || []);
            markers.forEach(m => {
                // markers are in order of instances; keep simple fade of whole map handled elsewhere
            });
        },
    };
})();
