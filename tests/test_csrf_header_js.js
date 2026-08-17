/* Jest tests for skydash/static/js/csrf-header.js
 * Module: IIFE that reads <meta name="csrf-token"> and wraps window.fetch to
 * attach the X-CSRFToken header. No public API returned. */
'use strict';

const fs = require('fs');
const path = require('path');

const SRC = fs.readFileSync(
    path.join(__dirname, '../skydash/static/js/csrf-header.js'), 'utf8');

/* Minimal Headers polyfill for jsdom environments that lack the Fetch API
 * (the module constructs `new Headers(...)` on every wrapped call). */
function HeadersPolyfill(init) {
    this._map = new Map();
    if (init) {
        if (init.forEach) init.forEach((v, k) => this._map.set(String(k).toLowerCase(), String(v)));
        else if (typeof init === 'object') {
            Object.keys(init).forEach((k) => this._map.set(k.toLowerCase(), String(init[k])));
        }
    }
}
HeadersPolyfill.prototype.has = function (name) { return this._map.has(String(name).toLowerCase()); };
HeadersPolyfill.prototype.get = function (name) { return this._map.get(String(name).toLowerCase()) || null; };
HeadersPolyfill.prototype.set = function (name, value) { this._map.set(String(name).toLowerCase(), String(value)); };

function evalModule() {
    new Function(SRC)();
}

describe('csrf-header.js IIFE module', () => {
    let fetchMock;

    beforeEach(() => {
        document.querySelectorAll('meta[name="csrf-token"]').forEach((m) => m.remove());
        if (typeof global.Headers === 'undefined') {
            global.Headers = HeadersPolyfill;
            window.Headers = HeadersPolyfill;
        }
        // The module replaces window.fetch with a wrapper; in jsdom window===global,
        // so reading global.fetch afterwards returns the wrapper. Capture the mock
        // in a closure variable instead.
        fetchMock = jest.fn();
        global.fetch = fetchMock;
        window.fetch = fetchMock;
    });

    afterEach(() => {
        document.querySelectorAll('meta[name="csrf-token"]').forEach((m) => m.remove());
    });

    function addMeta(content) {
        const meta = document.createElement('meta');
        meta.setAttribute('name', 'csrf-token');
        if (content !== null) meta.setAttribute('content', content);
        document.head.appendChild(meta);
    }

    it('leaves fetch untouched when no csrf meta exists', () => {
        const before = window.fetch;
        evalModule();
        expect(window.fetch).toBe(before);
        expect(window.fetch).toBe(fetchMock);
    });

    it('leaves fetch untouched when meta has no content attribute', () => {
        addMeta(null);
        const before = window.fetch;
        evalModule();
        expect(window.fetch).toBe(before);
    });

    it('wraps fetch when a token meta exists', () => {
        addMeta('tok-123');
        const before = window.fetch;
        evalModule();
        expect(window.fetch).not.toBe(before);
        expect(fetchMock).toHaveBeenCalledTimes(0);
    });

    it('attaches X-CSRFToken when request has no headers', () => {
        addMeta('tok-123');
        evalModule();
        window.fetch('/api/thing', { method: 'POST' });
        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, opts] = fetchMock.mock.calls[0];
        expect(url).toBe('/api/thing');
        expect(opts.headers.get('X-CSRFToken')).toBe('tok-123');
    });

    it('attaches X-CSRFToken when request has opaque object headers', () => {
        addMeta('sekret');
        evalModule();
        window.fetch('/api/x', { method: 'PUT', headers: { 'Content-Type': 'application/json' } });
        const [, opts] = fetchMock.mock.calls[0];
        expect(opts.headers.get('Content-Type')).toBe('application/json');
        expect(opts.headers.get('X-CSRFToken')).toBe('sekret');
    });

    it('does not override an existing X-CSRFToken', () => {
        addMeta('meta-token');
        evalModule();
        window.fetch('/api/y', { headers: { 'X-CSRFToken': 'explicit' } });
        const [, opts] = fetchMock.mock.calls[0];
        expect(opts.headers.get('X-CSRFToken')).toBe('explicit');
    });

    it('passes through request url and body unchanged', () => {
        addMeta('tok-9');
        evalModule();
        const body = JSON.stringify({ a: 1 });
        window.fetch('/api/z', { method: 'POST', body });
        const [url, opts] = fetchMock.mock.calls[0];
        expect(url).toBe('/api/z');
        expect(opts.body).toBe(body);
        expect(opts.headers.get('X-CSRFToken')).toBe('tok-9');
    });
});
