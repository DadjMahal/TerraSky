/* SkyDash — CSRF header helper (§77).
   Reads the token from <meta name="csrf-token"> (rendered server-side) and
   attaches it as an X-CSRFToken header to every unsafe fetch() request, so
   AJAX POST/PUT/DELETE calls pass Flask-WTF CSRF protection. */
(function () {
    'use strict';
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (!meta) return;
    var token = meta.getAttribute('content');
    if (!token) return;
    var orig = window.fetch;
    window.fetch = function (url, opts) {
        opts = opts || {};
        opts.headers = new Headers(opts.headers || {});
        if (!opts.headers.has('X-CSRFToken')) {
            opts.headers.set('X-CSRFToken', token);
        }
        return orig.call(this, url, opts);
    };
})();