/* ============================================================================
   SkyDash detail page JS — Category 2
   #11 tabs init  #12 actions loader (staged progress)  #19 domains CRUD
   Status badge + live refresh + log fetching (consolidated from old inline script).
   ============================================================================ */
(function () {
    "use strict";

    // Kept in sync with dashboard.js — see Documentation/FRONTEND_HANDBOOK.md.
    const STATUS_META = {
        running: { cls: "status-running", label: "Running" },
        stopped: { cls: "status-stopped", label: "Stopped" },
        starting: { cls: "status-starting beacon-pulse", label: "Starting" },
        stopping: { cls: "status-stopping beacon-pulse", label: "Stopping" },
        error: { cls: "status-error", label: "Error" },
        unknown: { cls: "status-unknown", label: "Unknown" },
        loading: { cls: "status-loading", label: "Loading" },
    };

    const SLUG = window.SKYDASH_SLUG;
    function showToast(msg, ok = true) {
        if (window.SkyDashDashboard?.showToast) return window.SkyDashDashboard.showToast(msg, ok);
        const stack = document.getElementById("toast-stack");
        if (!stack) return;
        const kind = ok ? "success" : "danger";
        const icon = ok ? "bi-check-circle-fill" : "bi-exclamation-triangle-fill";
        const el = document.createElement("div");
        el.className = `skydash-toast toast-${kind}`;
        el.style.setProperty("--toast-duration", "3500ms");
        el.innerHTML =
            `<div class="d-flex align-items-center gap-2 px-3 py-2">
                <i class="bi ${icon}"></i>
                <div class="flex-grow-1" style="font-size:var(--text-sm);">${String(msg).replace(/</g, "&lt;")}</div>
                <button type="button" class="btn-close-toast" aria-label="Dismiss"><i class="bi bi-x-lg"></i></button>
            </div>
            <div class="toast-progress"></div>`;
        el.querySelector(".btn-close-toast").addEventListener("click", () => el.remove());
        stack.appendChild(el);
        setTimeout(() => el.remove(), 3500);
    }

    function setBadge(status) {
        const m = STATUS_META[status] || STATUS_META.unknown;
        const el = document.getElementById("status-badge");
        if (el) {
            el.className = `status-pill ${m.cls}`;
            el.innerHTML = `<span class="beacon-dot"></span>${m.label}`;
            el.dataset.status = status;
        }
    }

    async function refreshStatus() {
        setBadge("loading");
        try {
            const res = await fetch(`/api/status/${SLUG}`, { cache: "no-store" });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const s = await res.json();
            setBadge(s.status);
            const pubEl = document.querySelector('[data-ip="public"]');
            const privEl = document.querySelector('[data-ip="private"]');
            if (pubEl && s.public_ip) pubEl.textContent = s.public_ip;
            if (privEl && s.private_ip) privEl.textContent = s.private_ip;
            const grp = document.getElementById("action-group");
            if (grp) grp.querySelectorAll('button[data-action="start"]').forEach(b => b.disabled = !s.can_manage);
            const dz = document.getElementById("danger-zone");
            if (dz) dz.querySelectorAll("button[data-danger-action]").forEach(b => b.disabled = !s.can_manage);
        } catch (e) { setBadge("error"); }
    }

    async function pollDetailStatus(targetState, onProgress) {
        for (let i = 0; i < 10; i++) {
            await new Promise(r => setTimeout(r, 3000));
            try {
                const res = await fetch(`/api/status/${SLUG}`, { cache: "no-store" });
                const s = await res.json();
                setBadge(s.status);
                if (s.status === targetState) return true;
                if (s.status === "error") return false;
                if (onProgress) onProgress(s.status);
            } catch (e) { /* keep polling */ }
        }
        return false;
    }

    // ---- #12 Actions loader (staged progress) ------------------------------
    function showProgress(stages) {
        const wrap = document.getElementById("action-progress");
        if (!wrap) return;
        wrap.innerHTML = stages.map((_, i) =>
            `<div class="stage" data-stage="${i}"><span class="dot"></span><span class="stage-text">${stages[i]}</span></div>`).join("");
        wrap.classList.add("show");
    }
    function setStage(i, state) {
        const wrap = document.getElementById("action-progress");
        if (!wrap) return;
        const stages = wrap.querySelectorAll(".stage");
        stages.forEach((s, idx) => {
            s.classList.remove("active", "done");
            if (idx < i) s.classList.add("done");
            if (idx === i && state !== "done") s.classList.add("active");
            if (idx === i && state === "done") s.classList.add("done");
        });
    }
    function hideProgress() {
        const wrap = document.getElementById("action-progress");
        if (wrap) wrap.classList.remove("show");
    }

    // ---- Action handler with staged progress (#12) -------------------------
    document.getElementById("action-group")?.addEventListener("click", async (ev) => {
        const btn = ev.target.closest("button[data-action]");
        if (!btn) return;
        const action = btn.dataset.action;
        const targetState = action === "start" ? "running" : "stopped";
        const label = action.charAt(0).toUpperCase() + action.slice(1);

        if (action === "refresh") {
            showToast("Refreshing status...", true);
            await refreshStatus();
            showToast("Status refreshed", true);
            return;
        }
        if (!confirm(`${label} this instance?`)) return;

        document.querySelectorAll("#action-group button[data-action]").forEach(b => b.disabled = true);
        const stages = [`Sending ${action} request to cloud API`, "Polling for status change", `Instance is ${targetState}`];
        showProgress(stages);
        setStage(0, "active");
        setBadge(action === "start" ? "starting" : "stopping");

        try {
            const res = await fetch(`/instance/${SLUG}/${action}`, { method: "POST" });
            const data = await res.json();
            if (!data.ok) { showToast(`${action} FAILED: ${data.message}`, false); setBadge("error"); setStage(0, "done"); return; }
            setStage(0, "done"); setStage(1, "active");
            const settled = await pollDetailStatus(targetState, () => {});
            setStage(1, "done");
            if (settled) { setStage(2, "done"); showToast(`${SLUG} is now ${targetState.toUpperCase()}`, true); }
            else { showToast(`${SLUG}: action sent but status not yet confirmed`, false); }
        } catch (e) {
            showToast(`${action} request failed: ${e.message}`, false);
            setBadge("error");
        } finally {
            setTimeout(hideProgress, 1500);
            refreshStatus();
        }
    });

    // ---- #17 Log fetching w/ syntax highlight ------------------------------
    function classify(line) {
        if (/ERROR/i.test(line)) return "lv-error";
        if (/WARN/i.test(line)) return "lv-warning";
        if (/INFO/i.test(line)) return "lv-info";
        return "";
    }
    window.renderLogLines = function (containerId, lines) {
        const c = document.getElementById(containerId);
        if (!c) return;
        if (!lines || !lines.length) { c.innerHTML = '<div class="text-muted">No logs available.</div>'; return; }
        c.innerHTML = lines.map(l => `<div class="lv-line ${classify(l)}">${String(l).replace(/</g, "&lt;")}</div>`).join("");
    };

    async function loadLogs(type) {
        const c = document.getElementById(`logs-${type}-content`);
        if (!c) return;
        c.innerHTML = '<div class="text-muted">Loading…</div>';
        try {
            const res = await fetch(`/logs/${SLUG}?type=${type}`, { cache: "no-store" });
            const data = await res.json();
            window.renderLogLines(`logs-${type}-content`, data.messages || []);
        } catch (e) { c.innerHTML = `<div class="text-danger">Failed: ${e.message}</div>`; }
    }
    window.loadLogs = loadLogs;
    window.scanLogs = function (type) {
        const t = type === "errors" ? "error" : type === "warnings" ? "warning" : "all";
        loadLogs(t);
        const summary = document.getElementById("scan-summary");
        const txt = document.getElementById("scan-summary-text");
        fetch(`/logs/${SLUG}/scan`).then(r => r.json()).then(d => {
            if (summary) summary.style.display = "block";
            if (txt) txt.textContent = `errors: ${d.summary?.errors ?? 0} · warnings: ${d.summary?.warnings ?? 0} · info: ${d.summary?.info ?? 0}`;
        }).catch(() => {});
    };
    window.refreshLogs = function () { ["all", "info", "warning", "error"].forEach(loadLogs); };


    // ---- #19 Domains CRUD --------------------------------------------------
    async function loadDomains() {
        const list = document.getElementById("domain-list");
        if (!list) return;
        try {
            const res = await fetch("/api/domains", { cache: "no-store" });
            const data = await res.json();
            if (!data.length) { list.innerHTML = '<div class="text-muted small">No custom domains mapped yet.</div>'; return; }
            list.innerHTML = data.map(m =>
                `<div class="domain-row"><div><code>${m.domain}</code> <i class="bi bi-arrow-right small text-faint"></i> ${m.slug}</div>
                 <button class="btn btn-sm btn-outline-danger" data-del="${m.domain}" title="Remove mapping"><i class="bi bi-trash3"></i></button></div>`).join("");
            list.querySelectorAll("button[data-del]").forEach(b => b.addEventListener("click", async () => {
                await fetch(`/api/domains?domain=${encodeURIComponent(b.dataset.del)}`, { method: "DELETE" });
                showToast("Domain mapping removed", true);
                loadDomains();
            }));
        } catch (e) { list.innerHTML = `<div class="text-danger">Failed: ${e.message}</div>`; }
    }
    document.getElementById("domain-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const form = e.target;
        const domain = form.domain.value.trim();
        if (!domain) return;
        const res = await fetch("/api/domains", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ domain, slug: SLUG }),
        });
        const data = await res.json();
        if (data.ok) { form.domain.value = ""; showToast("Domain mapped", true); loadDomains(); }
        else showToast(data.error || "Failed", false);
    });

    // ---- Init ---------------------------------------------------------------
    document.addEventListener("DOMContentLoaded", () => {
        refreshStatus();
        loadDomains();
        // Overview is the default active tab — shown.bs.tab won't fire on load,
        // so render the hardware specs chart proactively.
        if (window.SkyDashSpecs) window.SkyDashSpecs.render(SLUG);
        const logTab = document.querySelector('a[href="#tab-logs"]');
        if (logTab) logTab.addEventListener("shown.bs.tab", () => refreshLogs());
        const tabTriggers = document.querySelectorAll(".detail-tabs .nav-link[data-bs-toggle]");
        tabTriggers.forEach(t => t.addEventListener("shown.bs.tab", (e) => {
            const id = e.target.getAttribute("href");
            if (id === "#tab-overview" && window.SkyDashSpecs) window.SkyDashSpecs.render(SLUG);
            if (id === "#tab-metrics" && window.SkyDashMetrics) window.SkyDashMetrics.render(SLUG);
            if (id === "#tab-network") {
                if (window.SkyDashTopology) window.SkyDashTopology.render();
                if (window.SkyDashSecurityGroups) window.SkyDashSecurityGroups.render(SLUG);
            }
            if (id === "#tab-timeline" && window.SkyDashTimeline) window.SkyDashTimeline.render(SLUG);
            if (id === "#tab-ssh" && window.SkyDashSSHTerminal) window.SkyDashSSHTerminal.init(SLUG);
            if (id === "#tab-files" && window.SkyDashFileManager) window.SkyDashFileManager.init();
        }));
    });

    // ---- Danger-zone (#86): destructive ops need typed confirmation --------
    function typedConfirm(label, expected) {
        return new Promise((resolve) => {
            const modal = document.createElement("div");
            modal.className = "modal fade";
            modal.tabIndex = -1;
            modal.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                  <div class="modal-content">
                    <div class="modal-header">
                      <h5 class="modal-title"><i class="bi bi-exclamation-triangle me-2 text-danger"></i>${label}</h5>
                      <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                      <p>This is a destructive operation. Type <code>${expected}</code> to confirm.</p>
                      <input type="text" class="form-control" id="danger-input" placeholder="${expected}" autocomplete="off">
                    </div>
                    <div class="modal-footer">
                      <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                      <button type="button" class="btn btn-danger" id="danger-confirm" disabled>Confirm</button>
                    </div>
                  </div>
                </div>`;
            document.body.appendChild(modal);
            const m = new bootstrap.Modal(modal);
            const input = modal.querySelector("#danger-input");
            const confirmBtn = modal.querySelector("#danger-confirm");
            input.addEventListener("input", () => { confirmBtn.disabled = input.value.trim() !== expected; });
            confirmBtn.addEventListener("click", () => { m.hide(); modal.remove(); resolve(true); });
            modal.addEventListener("hidden.bs.modal", () => { modal.remove(); resolve(false); });
            m.show();
        });
    }

    const dangerZone = document.getElementById("danger-zone");
    if (dangerZone) {
        dangerZone.addEventListener("click", async (ev) => {
            const btn = ev.target.closest("button[data-danger-action]");
            if (!btn) return;
            const action = btn.dataset.dangerAction;
            const note = document.getElementById("danger-zone-note");
            if (note) note.textContent = "";
            const ok = await typedConfirm(`Stop ${SLUG}?`, SLUG);
            if (!ok) return;
            const stages = ["Sending stop request to cloud API", "Polling for status change", "Instance is stopped"];
            showProgress(stages);
            setStage(0, "active");
            setBadge("stopping");
            try {
                const res = await fetch(`/instance/${SLUG}/${action}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ approval: SLUG }) // §107 approval-token convention
                });
                const data = await res.json();
                if (!data.ok) {
                    if (note && (data.message || data.error)) note.textContent = data.message || data.error;
                    setStage(0, "done");
                    setBadge("error");
                    showToast(`${action} denied: ${data.message || data.error || "forbidden"}`, false);
                    return;
                }
                setStage(0, "done"); setStage(1, "active");
                const settled = await pollDetailStatus("stopped", () => {});
                setStage(1, "done");
                if (settled) { setStage(2, "done"); showToast(`${SLUG} is now STOPPED`, true); }
                else { showToast(`${SLUG}: stop sent but status not yet confirmed`, false); }
            } catch (e) {
                showToast(`${action} request failed: ${e.message}`, false);
                setBadge("error");
            } finally {
                setTimeout(hideProgress, 1500);
                refreshStatus();
            }
        });
    }

    window.SkyDashDetail = { refreshStatus, setBadge, showToast };
})();

