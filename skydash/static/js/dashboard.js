/* ============================================================================
   SkyDash dashboard JS — Category 1 UI/UX
   #5 filter (multi-select tags + type/region)  #6 drag-drop  #7 CPU/RAM bars
   #8 toasts  #9 context menu (quick actions)   #10 pagination / infinite scroll
   ============================================================================ */
(function () {
    "use strict";

    // ---- Status badge helpers ------------------------------------------------
    // Each status maps to a --status-* color token in tokens.css (see
    // Documentation/FRONTEND_HANDBOOK.md). Add new states in both places.
    const STATUS_META = {
        running: { cls: "status-running", label: "Running" },
        stopped: { cls: "status-stopped", label: "Stopped" },
        starting: { cls: "status-starting beacon-pulse", label: "Starting" },
        stopping: { cls: "status-stopping beacon-pulse", label: "Stopping" },
        error: { cls: "status-error", label: "Error" },
        unknown: { cls: "status-unknown", label: "Unknown" },
        loading: { cls: "status-loading", label: "Loading" },
    };
    function badgeHtml(status) {
        const m = STATUS_META[status] || STATUS_META.unknown;
        return `<span class="status-pill ${m.cls}" data-status-badge><span class="beacon-dot"></span>${m.label}</span>`;
    }
    function setCardStatus(card, status) {
        card.dataset.status = status;
        const el = card.querySelector("[data-status-badge]");
        if (el) el.outerHTML = badgeHtml(status);
        applyFilters();
    }

    // ---- Filter state -------------------------------------------------------
    const state = { selectedTags: new Set(), pageSize: 6, page: 0 };

    function allCards() {
        return Array.from(document.querySelectorAll("#cards .card-col"));
    }
    function visibleCards() {
        return allCards().filter(c => !c.classList.contains("hidden"));
    }

    // ---- #8 Toast stack -----------------------------------------------------
    function showToast(msg, ok = true, duration = 3500) {
        const stack = document.getElementById("toast-stack");
        if (!stack) return;
        const kind = ok ? "success" : "danger";
        const icon = ok ? "bi-check-circle-fill" : "bi-exclamation-triangle-fill";
        const el = document.createElement("div");
        el.className = `skydash-toast toast-${kind}`;
        el.style.setProperty("--toast-duration", duration + "ms");
        el.innerHTML =
            `<div class="d-flex align-items-center gap-2 px-3 py-2">
                <i class="bi ${icon}"></i>
                <div class="flex-grow-1" style="font-size:var(--text-sm);">${String(msg).replace(/</g, "&lt;")}</div>
                <button type="button" class="btn-close-toast" aria-label="Dismiss"><i class="bi bi-x-lg"></i></button>
            </div>
            <div class="toast-progress"></div>`;
        el.querySelector(".btn-close-toast").addEventListener("click", () => dismiss(el));
        stack.appendChild(el);
        setTimeout(() => dismiss(el), duration);
    }
    function dismiss(el) {
        if (el.dataset.dismissed) return;
        el.dataset.dismissed = "1";
        el.classList.add("hide-anim");
        setTimeout(() => el.remove(), 400);
    }

    // ---- #5 Filters ----------------------------------------------------------
    function collectTagOptions() {
        const panel = document.getElementById("tag-options");
        if (!panel) return;
        const seen = new Set();
        allCards().forEach(card => {
            let tags = {};
            try { tags = JSON.parse(card.dataset.tags || "{}"); } catch (e) { tags = {}; }
            Object.keys(tags).forEach(k => {
                const key = `${k}: ${tags[k]}`;
                if (seen.has(key)) return;
                seen.add(key);
                const id = "tag-" + key.replace(/[^a-zA-Z0-9-]/g, "-");
                const label = document.createElement("label");
                label.className = "form-check";
                label.innerHTML =
                    `<input class="form-check-input tag-check" type="checkbox" value="${key}" id="${id}">
                     <label class="form-check-label" for="${id}">${key}</label>`;
                panel.appendChild(label);
            });
        });
        panel.addEventListener("change", e => {
            if (!e.target.classList.contains("tag-check")) return;
            if (e.target.checked) state.selectedTags.add(e.target.value);
            else state.selectedTags.delete(e.target.value);
            updateTagCount();
            applyFilters();
        });
    }
    function updateTagCount() {
        const n = document.getElementById("tag-count");
        if (n) n.textContent = state.selectedTags.size ? " (" + state.selectedTags.size + ")" : "";
    }
    function cardMatchesTags(card) {
        if (state.selectedTags.size === 0) return true;
        let tags = {};
        try { tags = JSON.parse(card.dataset.tags || "{}"); } catch (e) { tags = {}; }
        for (const key of state.selectedTags) {
            const [k, v] = key.split(": ");
            if (tags[k] !== undefined && String(tags[k]) === v) return true;
        }
        return false;
    }
    function populateSelect(id, labelPrefix) {
        const sel = document.getElementById(id);
        if (!sel) return;
        sel.innerHTML = `<option value="">${labelPrefix}</option>`;
        const field = id.replace("filter-", "");
        const seen = new Set();
        allCards().forEach(c => {
            const v = (c.dataset[field] || "").toLowerCase();
            if (!v || seen.has(v)) return;
            seen.add(v);
            const o = document.createElement("option");
            o.value = v; o.textContent = v;
            sel.appendChild(o);
        });
    }
    function applyFilters() {
        const q = (document.getElementById("search")?.value || "").trim().toLowerCase();
        const fp = document.getElementById("filter-provider")?.value || "";
        const fs = document.getElementById("filter-status")?.value || "";
        const ft = document.getElementById("filter-type")?.value || "";
        const fr = document.getElementById("filter-region")?.value || "";
        allCards().forEach(card => {
            const hay = `${card.dataset.name} ${card.dataset.provider} ${card.dataset.type} ${card.dataset.region} ${card.dataset.slug} ${card.querySelector("[data-ip='public']")?.textContent || ""}`.toLowerCase();
            const show = (!q || hay.includes(q))
                && (!fp || card.dataset.provider === fp)
                && (!fs || card.dataset.status === fs)
                && (!ft || card.dataset.type === ft)
                && (!fr || card.dataset.region === fr)
                && cardMatchesTags(card);
            card.classList.toggle("hidden", !show);
        });
        renderPagination();
    }


    // ---- #6 Drag & drop reorder (Sortable + localStorage) -------------------
    function initSortable() {
        if (typeof Sortable === "undefined") return;
        const grid = document.getElementById("cards");
        if (!grid) return;
        Sortable.create(grid, {
            animation: 150,
            handle: ".card-header-drag",
            draggable: ".card-col",
            ghostClass: "dragging",
            onEnd() {
                const order = allCards().map(c => c.dataset.slug);
                try { localStorage.setItem("skydash-order", JSON.stringify(order)); } catch (e) {}
                showToast("Card order saved", true);
                renderPagination();
            },
        });
        grid.classList.add("sortable-active");
    }

    // ---- #10 Pagination / infinite scroll -----------------------------------
    function renderPagination() {
        const controls = document.getElementById("pagination-controls");
        const count = document.getElementById("load-count");
        const btn = document.getElementById("show-more");
        if (!controls) return;
        const vis = visibleCards();
        if (vis.length <= state.pageSize) {
            vis.forEach((c, i) => { c.classList.remove("hidden-by-page"); c.style.setProperty("--delay", Math.min(i * 0.03, 0.5) + "s"); });
            controls.style.display = "none";
            if (count) count.textContent = `${vis.length} / ${vis.length}`;
            return;
        }
        controls.style.display = "flex";
        const toShow = Math.min(vis.length, (state.page + 1) * state.pageSize);
        vis.forEach((c, i) => {
            c.classList.toggle("hidden-by-page", i >= toShow);
            c.style.setProperty("--delay", Math.min(i * 0.03, 0.5) + "s");
        });
        if (count) count.textContent = `${toShow} / ${vis.length}`;
        if (btn) btn.style.display = toShow >= vis.length ? "none" : "";
    }
    function initPagination() {
        const btn = document.getElementById("show-more");
        if (btn) btn.addEventListener("click", () => { state.page++; renderPagination(); });
        const sentinel = document.getElementById("scroll-sentinel");
        if (sentinel && "IntersectionObserver" in window) {
            new IntersectionObserver(entries => {
                if (entries[0].isIntersecting) {
                    const vis = visibleCards();
                    if (vis.length > (state.page + 1) * state.pageSize) { state.page++; renderPagination(); }
                }
            }, { rootMargin: "200px" }).observe(sentinel);
        }
    }

    // ---- Sort ---------------------------------------------------------------
    function applySort() {
        const key = document.getElementById("sort-by")?.value || "name";
        const grid = document.getElementById("cards");
        const cols = allCards();
        cols.sort((a, b) => (a.dataset[key] || "").localeCompare(b.dataset[key] || ""));
        cols.forEach(c => grid.appendChild(c));
        renderPagination();
    }

    // ---- #4 Region map toggle -----------------------------------------------
    function initMapToggle() {
        const btn = document.getElementById("map-toggle");
        const wrap = document.getElementById("region-map-wrap");
        if (!btn || !wrap) return;
        btn.addEventListener("click", () => {
            const showing = wrap.style.display !== "none";
            wrap.style.display = showing ? "none" : "block";
            btn.classList.toggle("active", !showing);
            if (!showing && window.SkyDashRegionMap) {
                window.SkyDashRegionMap.init(window.__SKYDASH_INSTANCES__ || []);
            }
        });
    }

    // ---- #7 CPU/RAM load ----------------------------------------------------
    async function fetchLoad() {
        try {
            const res = await fetch("/api/load", { cache: "no-store" });
            const data = await res.json();
            data.forEach(item => {
                const card = document.querySelector(`.card-col[data-slug="${item.slug}"]`);
                if (!card) return;
                const cpuBar = card.querySelector("[data-bar='cpu']");
                const ramBar = card.querySelector("[data-bar='ram']");
                if (cpuBar) cpuBar.style.width = (item.cpu_pct || 0) + "%";
                if (ramBar) ramBar.style.width = (item.ram_pct || 0) + "%";
                const cpuT = card.querySelector("[data-bar-label='cpu']");
                const ramT = card.querySelector("[data-bar-label='ram']");
                if (cpuT) cpuT.textContent = `${item.cpu_vcpus} vCPU`;
                if (ramT) ramT.textContent = `${item.ram_gb} GB`;
            });
        } catch (e) { /* non-fatal */ }
    }


    // ---- Live status polling -----------------------------------------------
    async function fetchStatuses(silent = true) {
        try {
            const res = await fetch("/api/statuses", { cache: "no-store" });
            const data = await res.json();
            data.forEach(s => {
                const card = document.querySelector(`.card-col[data-slug="${s.slug}"]`);
                if (!card) return;
                card.dataset.canManage = s.can_manage ? "1" : "0";
                setCardStatus(card, s.status);
                const pubEl = card.querySelector('[data-ip="public"]');
                const privEl = card.querySelector('[data-ip="private"]');
                if (pubEl && s.public_ip) pubEl.textContent = s.public_ip;
                if (privEl && s.private_ip) privEl.textContent = s.private_ip;
                const grp = card.querySelector("[data-actions]");
                if (grp) grp.querySelectorAll("button[data-action]").forEach(b => b.disabled = !s.can_manage);
                if (s.error && s.status === "error") card.title = s.error;
            });
            if (!silent) showToast("Statuses refreshed", true);
        } catch (e) { showToast("Failed to refresh statuses", false); }
    }

    // ---- Actions ------------------------------------------------------------
    function runAction(slug, action) {
        const card = document.querySelector(`.card-col[data-slug="${slug}"]`);
        if (action === "refresh") { setCardStatus(card, "loading"); fetchStatuses(true); return; }
        if (!confirm(`${action[0].toUpperCase() + action.slice(1)} instance "${slug}"?`)) return;
        if (card) card.querySelectorAll("button[data-action]").forEach(b => b.disabled = true);
        setCardStatus(card, action === "start" ? "starting" : "stopping");
        showToast(`Sending ${action} to ${slug}…`, true);
        fetch(`/instance/${slug}/${action}`, { method: "POST" })
            .then(r => r.json())
            .then(data => {
                if (!data.ok) { showToast(data.message || `${action} FAILED`, false); setCardStatus(card, "error"); }
                else { showToast(data.message, true); setTimeout(() => fetchStatuses(true), 2500); }
            })
            .catch(() => { showToast("Action request failed", false); setCardStatus(card, "error"); });
    }

    // ---- #9 Context menu -----------------------------------------------------
    function initContextMenu() {
        const menu = document.getElementById("context-menu");
        if (!menu) return;
        document.addEventListener("contextmenu", ev => {
            const card = ev.target.closest(".card-col");
            if (!card) return;
            ev.preventDefault();
            const can = card.dataset.canManage === "1";
            menu.dataset.slug = card.dataset.slug;
            document.getElementById("ctx-title").textContent = card.dataset.name;
            document.getElementById("ctx-start").disabled = !can;
            document.getElementById("ctx-stop").disabled = !can;
            document.getElementById("ctx-detail").href = `/instance/${card.dataset.slug}`;
            document.getElementById("ctx-logs").href = `/instance/${card.dataset.slug}#logs`;
            menu.classList.add("open");
            menu.style.left = Math.min(ev.clientX, window.innerWidth - 210) + "px";
            menu.style.top = Math.min(ev.clientY, window.innerHeight - 210) + "px";
        });
        document.addEventListener("click", ev => {
            if (!ev.target.closest("#context-menu")) menu.classList.remove("open");
        });
        menu.addEventListener("click", ev => {
            const btn = ev.target.closest("button[data-ctx-action]");
            if (!btn) return;
            runAction(menu.dataset.slug, btn.dataset.ctxAction);
            menu.classList.remove("open");
        });
    }

    // ---- Init ----------------------------------------------------------------
    document.addEventListener("DOMContentLoaded", () => {
        collectTagOptions();
        populateSelect("filter-type", "All types");
        populateSelect("filter-region", "All regions");

        document.getElementById("search")?.addEventListener("input", applyFilters);
        ["filter-provider", "filter-status", "filter-type", "filter-region"]
            .forEach(id => document.getElementById(id)?.addEventListener("change", applyFilters));
        document.getElementById("sort-by")?.addEventListener("change", applySort);

        const tagLabel = document.getElementById("tag-toggle");
        const tagPanel = document.getElementById("tag-options");
        if (tagLabel && tagPanel) {
            tagLabel.addEventListener("click", e => { e.stopPropagation(); tagPanel.classList.toggle("open"); });
            document.addEventListener("click", () => tagPanel.classList.remove("open"));
        }

        initMapToggle();
        initPagination();
        initSortable();
        initContextMenu();

        document.addEventListener("click", ev => {
            const btn = ev.target.closest("button[data-action]");
            if (!btn) return;
            const card = btn.closest(".card-col");
            if (card) runAction(card.dataset.slug, btn.dataset.action);
        });

        try {
            const saved = JSON.parse(localStorage.getItem("skydash-order") || "[]");
            if (Array.isArray(saved) && saved.length) {
                const grid = document.getElementById("cards");
                const bySlug = {};
                allCards().forEach(c => bySlug[c.dataset.slug] = c);
                saved.forEach(s => { if (bySlug[s]) grid.appendChild(bySlug[s]); });
            }
        } catch (e) {}
        applyFilters();
        fetchStatuses(true);
        fetchLoad();
        setInterval(() => fetchStatuses(true), 30000);
    });

    window.SkyDashDashboard = { applyFilters, showToast, fetchStatuses, fetchLoad };
})();

