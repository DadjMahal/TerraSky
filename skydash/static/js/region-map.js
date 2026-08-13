/* ============================================================================
   SkyDash — Task #4F Interactive Region Map (Futuristic Edition)

   Features:
   - Animated pulsing markers colored by provider with status beacon
   - Network connection lines between instances (topology visualization)
   - Hover tooltips + click popups with full instance details + detail page link
   - Smooth zoom, pan, and auto-fit to all markers
   - Connection lines pulse data flow; status reflects real-time state

   Renders a world map with a marker per provider region. Clicking a marker
   blinks/highlights the matching instance card on the dashboard.
   ============================================================================ */
(function () {
    "use strict";

    // Provider region -> [lat, lng]. Expand as new clouds/regions are added.
    const REGION_COORDS = {
        // AWS
        "us-east-1":     [38.9072, -77.0369],  // N. Virginia
        "us-west-1":     [37.7749, -122.4194], // N. California
        "eu-central-1":  [50.1109, 8.6821],    // Frankfurt
        "eu-west-1":     [53.3498, -6.2603],   // Ireland
        "ap-southeast-1":[1.3521, 103.8198],   // Singapore
        // Azure
        "polandcentral": [52.2297, 21.0122],
        "spaincentral":  [40.4168, -3.7038],
        "westeurope":    [51.5074, -0.1278],
        // Oracle
        "eu-frankfurt-1":[50.1109, 8.6821],
        "us-ashburn-1":  [38.9072, -77.0369],
        // Alibaba
        "cn-hangzhou":   [30.2760, 120.1320],
    };

    const PROVIDER_COLOR = {
        aws:     "#FF9900",
        azure:   "#0078D4",
        oracle:  "#F80000",
        alibaba: "#FF6A00",
    };

    const STATUS_COLOR = {
        running:  "#34D399",
        stopped:  "#8592B0",
        starting: "#FBBF24",
        stopping: "#FB923C",
        error:    "#FB7185",
        unknown:  "#6B7A9C",
        loading:  "#4FC8E8",
    };

    let map = null;
    let markers = [];
    let connectionLayers = [];
    let animationId = null;

    function coordFor(region) {
        if (!region) return null;
        return REGION_COORDS[String(region).toLowerCase()] || null;
    }

    // Create a futuristic animated marker icon (provider ring + status beacon pulse)
    function createMarkerIcon(inst) {
        const providerColor = PROVIDER_COLOR[inst.provider] || "#6c757d";
        const statusColor = STATUS_COLOR[inst.status] || "#6B7A9C";

        const html = `
        <div class="skydash-futuristic-marker" data-slug="${inst.slug}">
            <div class="fm-ring" style="border-color:${providerColor}; background:${providerColor};"></div>
            <div class="fm-pulse" style="background:${statusColor}; box-shadow:0 0 0 0 ${statusColor};"></div>
            <div class="fm-core" style="background:${statusColor}; border-color:${providerColor};"></div>
        </div>`;

        return L.divIcon({
            className: "futuristic-marker",
            html: html,
            iconSize: [26, 26],
            iconAnchor: [13, 13],
            popupAnchor: [0, -28],
        });
    }

    // Build popup HTML with instance details + link to detail page
    function popupHtml(inst) {
        const providerColor = PROVIDER_COLOR[inst.provider] || "#6c757d";
        const statusColor = STATUS_COLOR[inst.status] || "#6B7A9C";
        const badgeClass = `status-${inst.status || "unknown"}`;

        const tagsHtml = inst.tags
            ? Object.entries(inst.tags).map(([k, v]) => `<span class="tag-pill">${k}: ${v}</span>`).join("")
            : "";

        return `
        <div class="fm-popup">
            <div class="fm-popup-header">
                <span class="fm-provider-dot" style="background:${providerColor};"></span>
                <strong class="fm-name">${inst.name || inst.slug}</strong>
            </div>
            <div class="fm-popup-body">
                <div class="fm-pf-row"><span class="fm-pf-label">Provider</span><span class="fm-pf-value">${inst.provider || "—"}</span></div>
                <div class="fm-pf-row"><span class="fm-pf-label">Status</span><span class="fm-pf-value"><span class="status-pill ${badgeClass}"><span class="beacon-dot"></span>${inst.status || "unknown"}</span></span></div>
                <div class="fm-pf-row"><span class="fm-pf-label">Type</span><span class="fm-pf-value">${inst.instance_type || "—"}</span></div>
                <div class="fm-pf-row"><span class="fm-pf-label">Region</span><span class="fm-pf-value">${inst.region || "—"}</span></div>
                <div class="fm-pf-row"><span class="fm-pf-label">AZ</span><span class="fm-pf-value">${inst.availability_zone || "—"}</span></div>
                <div class="fm-pf-row"><span class="fm-pf-label">Public IP</span><span class="fm-pf-value fm-ip">${inst.public_ip || "—"}</span></div>
                <div class="fm-pf-row"><span class="fm-pf-label">Private IP</span><span class="fm-pf-value fm-ip">${inst.private_ip || "—"}</span></div>
                <div class="fm-pf-row"><span class="fm-pf-label">OS</span><span class="fm-pf-value">${inst.os || "—"}</span></div>
                <div class="fm-pf-row fm-pf-tags">${tagsHtml}</div>
            </div>
            <div class="fm-popup-footer">
                <a href="/instance/${inst.slug}" class="btn btn-sm btn-outline-primary fm-detail-link">Details <i class="bi bi-arrow-right"></i></a>
            </div>
        </div>`;
    }

    // Draw network connection lines between instances (topology visualization)
    function drawConnections(instances) {
        connectionLayers.forEach(layer => map.removeLayer(layer));
        connectionLayers = [];

        const validInstances = instances.filter(inst => coordFor(inst.region));
        if (validInstances.length < 2) return;

        const coords = validInstances.map(inst => ({
            slug: inst.slug,
            coord: coordFor(inst.region),
            provider: inst.provider,
            status: inst.status,
            color: PROVIDER_COLOR[inst.provider] || "#6c757d",
        }));

        // Determine "primary" — prefer AWS (gateways), then first running
        const primary = coords.find(c => c.provider === "aws" && c.status === "running")
                     || coords.find(c => c.status === "running")
                     || coords[0];

        coords.forEach((from, i) => {
            coords.forEach((to, j) => {
                if (i >= j) return; // avoid duplicate + self
                const isHub = (from === primary || to === primary);
                const lineColor = isHub ? "#4FC8E8" : "rgba(107,122,156,0.35)";
                const dashArray = isHub ? "4 3" : "2 6";
                const weight = isHub ? 2.5 : 1.2;

                const line = L.polyline([from.coord, to.coord], {
                    color: lineColor,
                    weight: weight,
                    opacity: 0.7,
                    dashArray: dashArray,
                    lineCap: "round",
                    smoothFactor: 0,
                }).addTo(map);

                connectionLayers.push(line);
            });
        });
    }

    // Animate connection line flow
    function animateConnectionFlow() {
        if (!map || connectionLayers.length === 0) return;
        const hubLines = connectionLayers.filter(l => l.options.dashArray === "4 3");
        hubLines.forEach((line, idx) => {
            line.setStyle({
                dashOffset: `${(Date.now() / 500 + idx * 0.5) % 7}`,
            });
        });
        animationId = requestAnimationFrame(animateConnectionFlow);
    }

    window.SkyDashRegionMap = {
        init(instances) {
            const wrap = document.getElementById("region-map");
            const errEl = document.getElementById("map-error");
            if (!wrap || map) return;

            // Lazy-load Leaflet
            if (!window.L) {
                if (errEl) errEl.textContent = "Loading map…";
                const s = document.createElement("script");
                s.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
                s.onload = () => window.SkyDashRegionMap.init(instances);
                s.onerror = () => { if (errEl) errEl.textContent = "Failed to load map library."; };
                document.head.appendChild(s);
                return;
            }

            try {
                map = L.map("region-map", {
                    scrollWheelZoom: false,
                    tap: false,
                    bounceAtZoomLimits: false,
                    inertia: true,
                    inertiaDeceleration: 3000,
                    inertiaMaxSpeed: 700,
                }).setView([42, 10], 2);

                // Dark futuristic tile layer (CartoDB dark matter)
                L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
                    maxZoom: 8,
                    minZoom: 1,
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
                    subdomains: "abcd",
                    detectRetina: true,
                                }).addTo(map);

                // Track bounds for auto-fit
                const bounds = L.latLngBounds();

                instances.forEach(inst => {
                    const c = coordFor(inst.region);
                    if (!c) return;

                    const latLng = L.latLng(c[0], c[1]);
                    bounds.extend(latLng);

                    const icon = createMarkerIcon(inst);
                    const m = L.marker(c, {
                        icon,
                        title: inst.name,
                        riseOnHover: true,
                        zIndexOffset: 500,
                    }).addTo(map);

                    // Bind rich popup with full instance details
                    m.bindPopup(popupHtml(inst), {
                        maxWidth: 320,
                        className: "fm-popup-wrapper",
                        closeButton: true,
                        autoClose: true,
                        closeOnEscape: true,
                    });

                    // Hover: highlight instance card on dashboard
                    m.on("mouseover", () => {
                        const card = document.querySelector(`.card-col[data-slug="${inst.slug}"]`);
                        if (card) card.classList.add("fm-card-highlight");
                    });
                    m.on("mouseout", () => {
                        const card = document.querySelector(`.card-col[data-slug="${inst.slug}"]`);
                        if (card) card.classList.remove("fm-card-highlight");
                    });

                    // Click: scroll to + highlight matching instance card
                    m.on("click", () => {
                        const card = document.querySelector(`.card-col[data-slug="${inst.slug}"]`);
                        if (card) {
                            card.scrollIntoView({ behavior: "smooth", block: "center" });
                            card.style.boxShadow = "0 0 0 3px var(--accent)";
                            setTimeout(() => { card.style.boxShadow = ""; }, 1500);
                        }
                    });

                    markers.push(m);
                });

                // Auto-fit map to all markers with padding
                if (bounds.isValid()) {
                    map.fitBounds(bounds.pad(0.25), { maxZoom: 2.5 });
                }

                // Draw network topology connections between instances
                drawConnections(instances);

                // Start connection line animation
                animateConnectionFlow();

                if (errEl) errEl.textContent = "";
            } catch (e) {
                if (errEl) errEl.textContent = "Map error: " + e.message;
                return;
            }
        },

        refresh(instances) {
            if (!map) return;
            markers.forEach(m => map.removeLayer(m));
            markers = [];
            connectionLayers.forEach(l => map.removeLayer(l));
            connectionLayers = [];
            window.SkyDashRegionMap.init(instances);
        },

        highlight(slugs) {
            const set = new Set(slugs || []);
            markers.forEach(m => {
                const el = m.getElement();
                if (el) el.style.opacity = set.size ? (set.has(m.options.title) ? "1" : "0.35") : "1";
            });
        },

        destroy() {
            if (animationId) cancelAnimationFrame(animationId);
            if (map) {
                map.remove();
                map = null;
            }
            markers = [];
            connectionLayers = [];
        },
    };
})();
