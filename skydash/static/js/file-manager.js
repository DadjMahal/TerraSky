/* ============================================================================\n   SkyDash — #20 File manager (dual-pane SFTP browser)\n   ============================================================================\n   Communicates with the Flask v1 file-manager routes:\n     GET  /api/v1/file/ls?slug=<slug>&path=<path>\n     GET  /api/v1/file/read?slug=<slug>&path=<path>&limit=<n>\n     POST /api/v1/file/write  (json: slug, path, content_b64)\n     POST /api/v1/file/delete (json: slug, path)\n     GET  /api/v1/file/stat?slug=<slug>&path=<path>\n     GET  /api/v1/file/disk?slug=<slug>&path=<path>\n\n   Dual-pane layout: left = directory tree (root + home subdirs), right = file\n   listing for the currently-browsed path.  Uses the Fetch API.  CSRF is\n   handled globally by csrf-header.js.\n   ============================================================================ */
(function () {
    "use strict";

    const SLUG = window.SKYDASH_SLUG;
    const INST = window.SKYDASH_INST || {};
    const API = "/api/v1/file";

    let currentPath = "/";

    /* ---- helpers ------------------------------------------------------ */
    function esc(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function fmtSize(n) {
        if (!n) return "";
        const units = ["B", "KB", "MB", "GB", "TB", "PB"];
        let i = 0;
        let val = n;
        while (val >= 1024 && i < units.length - 1) {
            val /= 1024;
            i++;
        }
        return val < 10 ? val.toFixed(1) + " " + units[i] : Math.round(val).toString() + " " + units[i];
    }

    function fmtDate(epoch) {
        if (!epoch) return "";
        return new Date(epoch * 1000).toLocaleString();
    }

    function iconFor(entry) {
        if (entry.type === "dir") return "bi bi-folder2-open";
        const ext = entry.name.split(".").pop().toLowerCase();
        const map = {
            js: "bi-filetype-js",
            py: "bi-filetype-py",
            sh: "bi-filetype-sh",
            json: "bi-filetype-json",
            yml: "bi-filetype-yml",
            yaml: "bi-filetype-yml",
            tf: "bi-filetype-text",
            txt: "bi-file-text",
            log: "bi-file-text",
            md: "bi-file-markdown",
            css: "bi-file-css",
            html: "bi-file-html",
            conf: "bi-gear",
        };
        return "bi bi-" + (map[ext] || "bi-file-earmark");
    }

    function showError(host, msg) {
        host.innerHTML =
            '<div class="alert alert-warning mb-0">' +
            '<i class="bi bi-exclamation-triangle me-2"></i>' +
            esc(msg) +
            "</div>";
    }

    /* ---- API calls ---------------------------------------------------- */
    async function fetchLs(path) {
        const q = new URLSearchParams({ slug: SLUG, path: path });
        const resp = await fetch(`${API}/ls?${q}`);
        const data = await resp.json();
        if (resp.status === 401) return { error: "Authentication required." };
        if (resp.status === 502) return { error: data.error || "Provider error." };
        if (!resp.ok) return { error: data.error || `HTTP ${resp.status}` };
        return data.data || {};
    }

    async function fetchRead(path, limit) {
        const q = new URLSearchParams({ slug: SLUG, path: path });
        if (limit) q.set("limit", limit);
        const resp = await fetch(`${API}/read?${q}`);
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
        return data.data || {};
    }

    async function fetchWrite(path, contentB64) {
        const resp = await fetch(`${API}/write`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ slug: SLUG, path: path, content_b64: contentB64 }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
        return data.data || {};
    }

    async function fetchDelete(path) {
        const resp = await fetch(`${API}/delete`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ slug: SLUG, path: path }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
        return data.data || {};
    }

    async function fetchDisk(path) {
        const q = new URLSearchParams({ slug: SLUG, path: path });
        const resp = await fetch(`${API}/disk?${q}`);
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
        return data.data || {};
    }

    /* ---- rendering ---------------------------------------------------- */
    function renderDisk(host) {
        fetchDisk(currentPath).then(d => {
            if (d.total === undefined) return;
            const pct = d.percent_used || 0;
            host.innerHTML =
                '<div class="small text-faint mb-2">' +
                '<i class="bi bi-device-hdd me-1"></i>' +
                esc("Disk: " + fmtSize(d.used) + " / " + fmtSize(d.total) + " used (" + pct + "%)") +
                "</div>";
        }).catch(() => {});
    }

    function renderListing(host) {
        fetchLs(currentPath).then(result => {
            if (result.error) {
                showError(host, result.error);
                return;
            }
            const entries = result.entries || [];
            if (!entries.length) {
                host.innerHTML = '<div class="small text-faint fst-italic">Directory is empty.</div>';
                return;
            }
            const rows = entries.map(function (e) {
                const isDir = e.type === "dir";
                return (
                    '<tr class="fm-row" data-path="' + esc(e.path) + '" data-type="' +
                    (isDir ? "dir" : "file") + '">' +
                    '<td class="fm-name"><i class="bi ' + iconFor(e) + ' me-2"></i>' + esc(e.name) + "</td>" +
                    '<td class="fm-type">' + esc(isDir ? "—" : fmtSize(e.size)) + "</td>" +
                    '<td class="fm-perms text-faint font-mono small">' + esc(e.perms_octal) + "</td>" +
                    '<td class="fm-mtime text-faint small">' + esc(fmtDate(e.mtime)) + "</td>" +
                    "</tr>"
                );
            }).join("");
            host.innerHTML =
                '<table class="table table-sm table-borderless table-hover mb-0 fm-table">' +
                '<thead><tr class="small text-uppercase text-faint">' +
                "<th>Name</th><th>Size</th><th>Perms</th><th>Modified</th></tr></thead><tbody>" +
                rows + "</tbody></table>";
        }).catch(err => showError(host, err.message));
    }

    /* ---- interaction -------------------------------------------------- */
    function handleRowClick(ev) {
        const row = ev.target.closest(".fm-row");
        if (!row) return;
        const path = row.dataset.path;
        const isDir = row.dataset.type === "dir";
        if (isDir) {
            currentPath = path;
            navigate(currentPath);
        }
    }

    function handleContextMenu(ev) {
        ev.preventDefault();
        const row = ev.target.closest(".fm-row");
        if (!row) return;
        const path = row.dataset.path;
        const name = row.querySelector(".fm-name").textContent.trim();

        const menu = document.createElement("div");
        menu.className = "fm-context-menu";
        menu.style.cssText =
            "position:absolute;z-index:2000;background:var(--surface);border:1px solid var(--border);" +
            "border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,.4);min-width:160px;";

        const add = (label, icon, onclick) => {
            const item = document.createElement("button");
            item.className = "d-block w-100 text-start px-2 py-1 bg-transparent border-0 small";
            item.innerHTML = '<i class="bi ' + icon + ' me-2"></i>' + label;
            item.onclick = () => {
                document.body.removeChild(menu);
                onclick();
            };
            menu.appendChild(item);
        };

        add("View " + name, "bi-eye", () => viewFile(path));
        add("Delete", "bi-trash3", () => deleteItem(path, name));
        document.body.appendChild(menu);
        menu.style.left = ev.pageX + "px";
        menu.style.top = ev.pageY + "px";
        document.addEventListener("click", () => document.body.removeChild(menu), { once: true });
    }

    async function viewFile(path) {
        try {
            const d = await fetchRead(path);
            const content = d.content || "";
            const modal = document.createElement("div");
            modal.className = "modal fade";
            modal.tabIndex = -1;
            modal.innerHTML =
                '<div class="modal-dialog modal-xl modal-dialog-scrollable">' +
                '<div class="modal-content">' +
                '<div class="modal-header"><h5 class="modal-title">' +
                '<i class="bi bi-file-text me-2"></i>' + esc(path) + "</h5>" +
                '<button type="button" class="btn-close" data-bs-dismiss="modal"></button>' +
                "</div>" +
                '<div class="modal-body"><pre class="mb-0 font-mono small" ' +
                'style="white-space:pre-wrap;word-break:break-word;">' + esc(content) + "</pre></div>" +
                '<div class="modal-footer"><button type="button" class="btn btn-sm btn-outline-secondary" ' +
                'data-bs-dismiss="modal">Close</button></div>' +
                "</div></div>";
            document.body.appendChild(modal);
            const m = new bootstrap.Modal(modal);
            m.show();
            modal.addEventListener("hidden.bs.modal", () => modal.remove());
        } catch (err) {
            window.SkyDashFileManager?.showToast(err.message, false);
        }
    }

    async function deleteItem(path, name) {
        if (!confirm("Delete " + name + "? This cannot be undone.")) return;
        try {
            await fetchDelete(path);
            window.SkyDashFileManager?.showToast("Deleted " + name, true);
            navigate(currentPath);
        } catch (err) {
            window.SkyDashFileManager?.showToast(err.message, false);
        }
    }

    /* ---- navigation --------------------------------------------------- */
    function breadcrumb(path) {
        const host = document.getElementById("fm-breadcrumb");
        if (!host) return;
        const parts = path.split("/").filter(Boolean);
        let html = '<a href="#" class="fm-bc-root" data-path="/">Home</a>';
        let accum = "/";
        for (let i = 0; i < parts.length; i++) {
            accum += parts[i] + "/";
            html +=
                ' <i class="bi bi-chevron-right text-faint small"></i> ' +
                '<a href="#" data-path="' + esc(accum) + '">' + esc(parts[i]) + "</a>";
        }
        host.innerHTML = html;
    }

    function navigate(path) {
        currentPath = path || "/";
        breadcrumb(currentPath);
        renderListing(document.getElementById("fm-listing"));
        renderDisk(document.getElementById("fm-disk"));
    }

    function setupTree() {
        const tree = document.getElementById("fm-tree");
        if (!tree) return;
        const roots = ["/", "/home", "/etc", "/var", "/opt", "/tmp", "/root"];
        tree.innerHTML = roots.map(function (r) {
            return (
                '<div class="fm-tree-item" data-path="' + esc(r) + '">' +
                '<span class="text-faint small">' + esc(r) + "</span>" +
                "</div>"
            );
        }).join("");
        tree.addEventListener("click", function (ev) {
            const item = ev.target.closest(".fm-tree-item");
            if (!item) return;
            navigate(item.dataset.path);
        });
    }

    /* ---- public API --------------------------------------------------- */
    function init() {
        if (!SLUG) return;

        setupTree();

        const listing = document.getElementById("fm-listing");
        if (listing) {
            listing.addEventListener("click", handleRowClick);
            listing.addEventListener("contextmenu", handleContextMenu);
        }

        const bc = document.getElementById("fm-breadcrumb");
        if (bc) {
            bc.addEventListener("click", function (ev) {
                const a = ev.target.closest("a[data-path]");
                if (!a) return;
                ev.preventDefault();
                navigate(a.dataset.path);
            });
        }

        // Upload button
        const uploadBtn = document.getElementById("fm-upload");
        if (uploadBtn) {
            uploadBtn.addEventListener("click", async () => {
                const input = document.createElement("input");
                input.type = "file";
                input.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (!file) return;
                    const reader = new FileReader();
                    reader.onload = async () => {
                        const b64 = btoa(String.fromCharCode(...new Uint8Array(reader.result)));
                        const targetPath =
                            (currentPath.endsWith("/") ? currentPath : currentPath + "/") + file.name;
                        try {
                            await fetchWrite(targetPath, b64);
                            window.SkyDashFileManager?.showToast("Uploaded " + file.name, true);
                            navigate(currentPath);
                        } catch (err) {
                            window.SkyDashFileManager?.showToast(err.message, false);
                        }
                    };
                    reader.readAsArrayBuffer(file);
                };
                input.click();
            });
        }

        navigate("/");
    }

    function showToast(msg, ok) {
        if (window.SkyDashDetail?.showToast) return window.SkyDashDetail.showToast(msg, ok);
    }

    window.SkyDashFileManager = { init, navigate, showToast };

    /* ---- lazy init: only set up listeners now; actual render on tab show */
    let _initialized = false;
    document.addEventListener("DOMContentLoaded", function () {
        if (document.getElementById("fm-listing")) {
            _initialized = true;
        }
    });

        document.addEventListener("shown.bs.tab", function (e) {
        if (!e.target) return;
        const href = e.target.getAttribute("href");
        if (href === "#tab-files" && _initialized) {
            init();
        }
    });
})();
