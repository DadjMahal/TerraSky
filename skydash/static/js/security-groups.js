/* ============================================================================
   SkyDash — Network Security Groups panel (Task 4)
   Fetches normalized SG/firewall data from the provider via the v1 API and
   renders inbound/outbound rule tables with provider color coding.
   ============================================================================ */
(function () {
    "use strict";

    var SLUG = window.SKYDASH_SLUG;
    var INST = window.SKYDASH_INST || {};

    // Provider -> CSS color (mirrors static/css/tokens.css --provider-*)
    var PROVIDER_COLORS = {
        aws: "#FF9900",
        azure: "#0078D4",
        oracle: "#F80000",
        alibaba: "#FF6A00",
        digitalocean: "#0080FF",
    };

    function providerColor(provider) {
        return PROVIDER_COLORS[provider] || "#6c757d";
    }

    function typeLabel(sg) {
        return sg.type || "Security Group";
    }

    function esc(html) {
        return String(html == null ? "" : html)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function ruleRow(rule) {
        var actionCls = rule.action === "deny" ? "text-danger" : "text-success";
        return "<tr>" +
            "<td class=\"font-mono small\">" + esc(rule.protocol) + "</td>" +
            "<td class=\"font-mono small\">" + esc(rule.port || "all") + "</td>" +
            "<td class=\"font-mono small text-truncate\" style=\"max-width:220px;\" title=\"" + esc(rule.source) + "\">" + esc(rule.source || "0.0.0.0/0") + "</td>" +
            "<td><span class=\"" + actionCls + " fw-medium\">" + esc(rule.action || "allow") + "</span></td>" +
            "<td class=\"small text-faint\">" + esc(rule.description) + "</td>" +
            "</tr>";
    }

    function renderTable(rules) {
        if (!rules || !rules.length) {
            return '<div class="small text-faint fst-italic">No rules in this policy.</div>';
        }
        return '<table class="table table-sm table-borderless align-middle mb-0">' +
            '<thead><tr class="small text-uppercase text-faint">' +
            "<th>Protocol</th><th>Port(s)</th><th>Source / Destination</th>" +
            "<th>Action</th><th>Description</th></tr></thead><tbody>" +
            rules.map(ruleRow).join("") +
            "</tbody></table>";
    }

    function renderGroup(sg) {
        var color = providerColor(sg.provider);
        return '<div class="card mb-3 bg-surface-1 border-secondary">' +
            '<div class="card-header d-flex align-items-center justify-content-between" ' +
            'style="border-color:' + color + '">' +
            '<div class="d-flex align-items-center gap-2">' +
            '<span class="provider-dot" style="background:' + color + ';width:12px;height:12px;border-radius:50%"></span>' +
            '<span class="fw-medium">' + esc(sg.name || sg.id) + "</span>" +
            '<span class="badge bg-secondary-subtle text-secondary-emphasis fs-12">' + esc(typeLabel(sg)) + "</span>" +
            "</div>" +
            '<span class="badge bg-dark bg-opacity-10 text-faint fs-12">' + esc(sg.provider) + "</span>" +
            "</div>" +
            '<div class="card-body p-3">' +
            '<div class="row g-0">' +
            '<div class="col-12 col-md-6 border-end border-secondary pe-md-3 mb-3 mb-md-0">' +
            '<h4 class="h6 fw-medium mb-2"><i class="bi bi-box-arrow-in-down"></i> Inbound</h4>' +
            renderTable(sg.inbound) +
            "</div>" +
            '<div class="col-12 col-md-6 ps-md-3">' +
            '<h4 class="h6 fw-medium mb-2"><i class="bi bi-box-arrow-up"></i> Outbound</h4>' +
            renderTable(sg.outbound) +
            "</div>" +
            "</div>" +
            "</div>" +
            "</div>";
    }

    function render(groups) {
        var host = document.getElementById("security-groups-host");
        if (!host) return;
        if (!groups || !groups.length) {
            host.innerHTML = '<div class="small text-faint fst-italic">No security groups or firewalls found for this instance.</div>';
            return;
        }
        host.innerHTML = groups.map(renderGroup).join("");
    }

    function showError(msg) {
        var host = document.getElementById("security-groups-host");
        if (!host) return;
        host.innerHTML = '<div class="alert alert-warning mb-0">' +
            '<i class="bi bi-exclamation-triangle"></i> ' + esc(msg) + "</div>";
    }

    function fetchSecurityGroups() {
        var url = "/api/v1/instance/" + encodeURIComponent(SLUG) + "/security-groups";
        fetch(url, { headers: { "X-CSRF-Token": window.CSRF_TOKEN || "" } })
            .then(function (r) {
                if (r.status === 401) {
                    showError("Authentication required to view security groups.");
                    return null;
                }
                if (r.status === 503) {
                    showError("Provider credentials unavailable; security groups cannot be fetched.");
                    return null;
                }
                if (r.status === 502) {
                    showError("Provider error while fetching security groups.");
                    return null;
                }
                if (!r.ok) {
                    showError("Failed to fetch security groups (HTTP " + r.status + ").");
                    return null;
                }
                return r.json();
            })
            .then(function (payload) {
                if (!payload) return;
                var groups = payload.status === "ok"
                    ? payload.data
                    : (payload.groups || []);
                render(groups || []);
            })
            .catch(function (err) {
                showError("Error: " + ((err && err.message) || "network failure"));
            });
    }

    // Init on DOM ready. The Network tab may not be active, so we fetch lazily
    // when the tab is shown as well.
    function init() {
        var badge = document.getElementById("sg-provider-badge");
        if (badge && INST.provider_label) {
            badge.textContent = INST.provider_label;
        }
        fetchSecurityGroups();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    // Re-fetch when the user opens the Network tab (Bootstrap pill shown event).
    document.addEventListener("shown.bs.tab", function (e) {
        var target = e.target;
        if (target && target.getAttribute && target.getAttribute("data-bs-target") === "#tab-network") {
            fetchSecurityGroups();
        }
    });

    // Expose for testing / manual refresh.
    window.SkyDashSecurityGroups = { fetch: fetchSecurityGroups, render: render };
})();
