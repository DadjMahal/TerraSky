/* SkyDash — Notification center (§60).
   Polls GET /api/v1/notifications (status transitions across the fleet) and
   renders newest-first into the navbar bell dropdown (base.html). */
(function () {
    'use strict';
    var wrap = document.getElementById('notif-wrap');
    if (!wrap) return;
    var menu = document.getElementById('notif-menu');
    var empty = document.getElementById('notif-empty');
    var countBadge = document.getElementById('notif-count');

    function fmt(ts) {
        if (!ts) return 'recently';
        try { return new Date(ts * 1000).toLocaleString(); } catch (e) { return 'recently'; }
    }

    async function load() {
        try {
            var res = await fetch('/api/v1/notifications', { cache: 'no-store' });
            var body = await res.json();
            var items = (body && body.data && body.data.notifications) || [];
            var existing = menu.querySelectorAll('.notif-item');
            existing.forEach(function (n) { n.remove(); });
            if (!items.length) {
                if (empty) empty.classList.remove('d-none');
                if (countBadge) countBadge.classList.add('d-none');
                return;
            }
            if (empty) empty.classList.add('d-none');
            items.slice(0, 8).forEach(function (ev) {
                var li = document.createElement('li');
                li.className = 'notif-item';
                var st = ev.status || 'unknown';
                var color = st === 'running' ? 'success' : (st === 'error' ? 'danger' : 'warning');
                li.innerHTML = '<a class="dropdown-item" href="/detail/' + (ev.slug || '') + '">' +
                    '<span class="small"><span class="text-' + color + '">●</span> <code>' + (ev.slug || '?') + '</code> → ' + st + '</span>' +
                    '<div class="small text-faint">' + fmt(ev.ts) + '</div></a>';
                menu.appendChild(li);
            });
            if (countBadge) {
                countBadge.textContent = items.length > 99 ? '99+' : items.length;
                countBadge.classList.remove('d-none');
            }
        } catch (e) { /* silent: notification bell must never block the UI */ }
    }

    var bell = wrap.querySelector('button[data-bs-toggle="dropdown"]');
    if (bell) bell.addEventListener('show.bs.dropdown', load);
    load();
})();