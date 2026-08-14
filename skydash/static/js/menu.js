/* ===========================================================================
   SkyDash — Sidebar navigation toggle (Task 1)

   Collapses/expands the left sidebar and persists the state in localStorage
   so the user's preference is remembered across page loads.

   On desktop: toggles the `collapsed` CSS class (width → 0).
   On mobile:   toggles the `show` CSS class (translateX drawer).
   ========================================================================= */
(function () {
    "use strict";

    var STORAGE_KEY = "skydash-sidebar-collapsed";
    var sidebar = document.getElementById("skydash-sidebar");
    var toggleBtn = document.getElementById("sidebar-toggle-btn");

    if (!sidebar || !toggleBtn) return;

    var mq = window.matchMedia("(min-width: 768px)");

    function setCollapsed(collapsed) {
        if (collapsed) {
            sidebar.classList.add("collapsed");
            document.body.classList.add("sidebar-collapsed");
            toggleBtn.setAttribute("aria-label", "Expand sidebar");
        } else {
            sidebar.classList.remove("collapsed");
            document.body.classList.remove("sidebar-collapsed");
            toggleBtn.setAttribute("aria-label", "Collapse sidebar");
        }
        localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
    }

    function isCollapsed() {
        return localStorage.getItem(STORAGE_KEY) === "1";
    }

    // Restore persisted state on load
    setCollapsed(isCollapsed());

    function syncMobileState() {
        if (!mq.matches) {
            sidebar.classList.remove("show");
        }
    }

    toggleBtn.addEventListener("click", function () {
        if (!mq.matches) {
            // Mobile: toggle translateX drawer
            sidebar.classList.toggle("show");
        } else {
            // Desktop: toggle width collapse
            setCollapsed(!sidebar.classList.contains("collapsed"));
        }
    });

    // Close mobile sidebar on ESC
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && sidebar.classList.contains("show")) {
            sidebar.classList.remove("show");
        }
    });

    // Re-sync on breakpoint change
    mq.addEventListener("change", syncMobileState);

    // Region map toggle from sidebar link
    var mapToggles = document.querySelectorAll("[data-map-toggle]");
    mapToggles.forEach(function (el) {
        el.addEventListener("click", function (e) {
            e.preventDefault();
            var mapToggle = document.getElementById("map-toggle");
            if (mapToggle) {
                mapToggle.click();
            }
        });
    });

    // Expose for external use
    window.SkyDashSidebar = {
        collapse: function () { setCollapsed(true); },
        expand: function () { setCollapsed(false); },
        toggle: function () {
            if (mq.matches) {
                setCollapsed(!sidebar.classList.contains("collapsed"));
            } else {
                sidebar.classList.toggle("show");
            }
        },
        isCollapsed: isCollapsed,
    };
})();
