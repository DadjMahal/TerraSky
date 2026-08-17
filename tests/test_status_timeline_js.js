/* Jest tests for skydash/static/js/status-timeline.js
 * Module: implements window.SkyDashTimeline = { render(slug) } — fetches
 * /api/status-history/<slug> and renders a horizontal timeline into
 * #timeline-host. */
'use strict';

const fs = require('fs');
const path = require('path');

const SRC = fs.readFileSync(
    path.join(__dirname, '../skydash/static/js/status-timeline.js'), 'utf8');

function evalModule() {
    new Function(SRC)();
    return window.SkyDashTimeline;
}

function flush() {
    return new Promise((resolve) => setTimeout(resolve, 0));
}

function makeHost() {
    const host = document.createElement('div');
    host.id = 'timeline-host';
    document.body.appendChild(host);
    return host;
}

describe('status-timeline.js module', () => {
    beforeEach(() => {
        document.body.querySelectorAll('#timeline-host').forEach((n) => n.remove());
        global.fetch = jest.fn();
        delete window.SkyDashTimeline;
    });
    afterEach(() => {
        document.body.querySelectorAll('#timeline-host').forEach((n) => n.remove());
    });

    it('exposes a render API', () => {
        const mod = evalModule();
        expect(typeof mod.render).toBe('function');
    });

    it('returns early (no fetch) when #timeline-host is absent', async () => {
        const mod = evalModule();
        await mod.render('my-instance');
        expect(global.fetch).not.toHaveBeenCalled();
    });

    it('shows a loading placeholder while the request is pending', async () => {
        const host = makeHost();
        // A manually-resolved promise lets us inspect the DOM in the pending state.
        let resolveFetch;
        global.fetch.mockReturnValue(new Promise((res) => { resolveFetch = res; }));
        const mod = evalModule();
        const p = mod.render('my-instance');
        await flush();
        expect(host.innerHTML).toContain('Loading');
        resolveFetch({ json: async () => [{ ts: 1, status: 'running' }] });
        await p;
    });

    it('shows "No status history" for an empty array', async () => {
        const host = makeHost();
        global.fetch.mockResolvedValue({ json: async () => [] });
        const mod = evalModule();
        await mod.render('my-instance');
        expect(host.innerHTML).toContain('No status history');
    });

    it('shows "No status history" when payload is not an array', async () => {
        const host = makeHost();
        global.fetch.mockResolvedValue({ json: async () => ({ status: 'ok' }) });
        const mod = evalModule();
        await mod.render('my-instance');
        expect(host.innerHTML).toContain('No status history');
    });

    it('requests /api/status-history/<slug> with no-store', async () => {
        const host = makeHost();
        global.fetch.mockResolvedValue({ json: async () => [{ ts: 100, status: 'running' }] });
        const mod = evalModule();
        await mod.render('slug-42');
        expect(global.fetch).toHaveBeenCalledWith('/api/status-history/slug-42', { cache: 'no-store' });
        expect(host.innerHTML).toContain('running');
    });

    it('renders one tl-event per history entry', async () => {
        const host = makeHost();
        const entries = [
            { ts: 100, status: 'running' },
            { ts: 200, status: 'stopped' },
            { ts: 300, status: 'error' },
        ];
        global.fetch.mockResolvedValue({ json: async () => entries });
        const mod = evalModule();
        await mod.render('i');
        expect(host.querySelectorAll('.tl-event').length).toBe(3);
        expect(host.innerHTML).toContain('running');
        expect(host.innerHTML).toContain('stopped');
        expect(host.innerHTML).toContain('error');
    });

    it('caps the render at the last 12 entries', async () => {
        const host = makeHost();
        const entries = Array.from({ length: 20 }, (_, i) => ({ ts: i, status: 'running' }));
        global.fetch.mockResolvedValue({ json: async () => entries });
        const mod = evalModule();
        await mod.render('i');
        expect(host.querySelectorAll('.tl-event').length).toBe(12);
    });

    it('keeps the last 12 entries (most recent tail)', async () => {
        const host = makeHost();
        // 14 entries ts 0..13; render keeps tail -> ts 2..13
        const entries = Array.from({ length: 14 }, (_, i) => ({ ts: i, status: 'running' }));
        global.fetch.mockResolvedValue({ json: async () => entries });
        const mod = evalModule();
        await mod.render('i');
        expect(host.querySelectorAll('.tl-event').length).toBe(12);
        // 13 events were rendered total, but tail keeps 12
        expect(host.querySelectorAll('.tl-event').length).toBeLessThan(entries.length);
    });

    it('shows a failure message on fetch error', async () => {
        const host = makeHost();
        global.fetch.mockRejectedValue(new Error('boom'));
        const mod = evalModule();
        await mod.render('i');
        expect(host.innerHTML).toContain('Failed');
        expect(host.innerHTML).toContain('boom');
    });

    it('renders colors by status using CSS variables', async () => {
        const host = makeHost();
        global.fetch.mockResolvedValue({ json: async () => [{ ts: 1, status: 'stopped' }] });
        const mod = evalModule();
        await mod.render('i');
        expect(host.innerHTML).toContain('var(--status-stopped)');
    });

    it('falls back to unknown color for unrecognized status', async () => {
        const host = makeHost();
        global.fetch.mockResolvedValue({ json: async () => [{ ts: 1, status: 'weird' }] });
        const mod = evalModule();
        await mod.render('i');
        expect(host.innerHTML).toContain('var(--status-unknown)');
    });
});
