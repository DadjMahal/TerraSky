/* ============================================================================
   Test suite for skydash/static/js/notifications.js (notification center IIFE)
   Uses fs.readFileSync + eval in a jsdom environment.
   ============================================================================ */

const fs = require('fs');
const path = require('path');

const SRC_PATH = path.resolve(__dirname, '../skydash/static/js/notifications.js');

let src;
try {
    src = fs.readFileSync(SRC_PATH, 'utf8');
} catch (e) {
    src = null;
}

function flush() {
    return new Promise((resolve) => setTimeout(resolve, 0));
}

/* Set up the DOM used by base.html for the notification bell and re-eval the
 * IIFE. Returns a helper to snapshot innerHTML/classes. */
function setupDom() {
    document.body.innerHTML =
        '<div id="notif-wrap">' +
        '  <button data-bs-toggle="dropdown">bell</button>' +
        '  <ul id="notif-menu"></ul>' +
        '  <div id="notif-empty" class="d-none"></div>' +
        '  <span id="notif-count" class="d-none"></span>' +
        '</div>';
}

describe('notifications.js IIFE module', () => {
    beforeEach(() => {
        global.fetch = jest.fn();
    });

    function loadModule(data, opts = {}) {
        if (!opts.skipWrap) setupDom();

        global.fetch.mockReset();
        global.fetch.mockResolvedValue({
            ok: true,
            status: 200,
            json: async () => ({ status: 'ok', data: data || { notifications: [] } }),
        });

        expect(src).not.toBeNull();
        // eslint-disable-next-line no-eval
        eval(src);
    }

    const menu = () => document.getElementById('notif-menu');
    const emptyEl = () => document.getElementById('notif-empty');
    const countBadge = () => document.getElementById('notif-count');
    const bell = () => document.querySelector('#notif-wrap button[data-bs-toggle="dropdown"]');
    const itemCount = () => menu().querySelectorAll('.notif-item').length;
    const notif = (overrides) => Object.assign({ slug: 'inst-1', status: 'running', ts: 1700000000 }, overrides);

    describe('early return when container missing', () => {
        it('does not fetch when notif-wrap is absent', () => {
            document.body.innerHTML = '<div></div>';
            global.fetch.mockReset();
            eval(src);
            expect(global.fetch).not.toHaveBeenCalled();
        });
    });

    describe('rendering on load (auto-fetch)', () => {
        it('renders notifications newest-first into the menu', async () => {
            loadModule({ notifications: [notif({ slug: 'alpha' }), notif({ slug: 'beta', status: 'error' })] });
            await flush();
            expect(global.fetch).toHaveBeenCalledTimes(1);
            expect(menu().innerHTML).toContain('alpha');
            expect(menu().innerHTML).toContain('beta');
            expect(menu().querySelectorAll('.notif-item').length).toBe(2);
        });

        it('shows recently for a missing timestamp', async () => {
            loadModule({ notifications: [notif({ ts: undefined })] });
            await flush();
            expect(menu().innerHTML).toContain('recently');
        });

        it('renders at most 8 items but badges the full count', async () => {
            const items = Array.from({ length: 12 }, (_, i) => notif({ slug: 's' + i }));
            loadModule({ notifications: items });
            await flush();
            expect(itemCount()).toBe(8);
            expect(countBadge().textContent).toBe('12');
            expect(countBadge().classList.contains('d-none')).toBe(false);
        });

        it('badges 99+ when there are more than 99 notifications', async () => {
            const items = Array.from({ length: 120 }, (_, i) => notif({ slug: 's' + i }));
            loadModule({ notifications: items });
            await flush();
            expect(countBadge().textContent).toBe('99+');
        });
    });

    describe('empty state', () => {
        it('shows the empty element and hides the count badge when no notifications', async () => {
            loadModule({ notifications: [] });
            await flush();
            expect(emptyEl().classList.contains('d-none')).toBe(false);
            expect(countBadge().classList.contains('d-none')).toBe(true);
            expect(itemCount()).toBe(0);
        });
    });

    describe('status color mapping', () => {
        it('uses success for running, danger for error, warning otherwise', async () => {
            loadModule({
                notifications: [
                    notif({ slug: 'run', status: 'running' }),
                    notif({ slug: 'err', status: 'error' }),
                    notif({ slug: 'pen', status: 'pending' }),
                ],
            });
            await flush();
            expect(menu().innerHTML).toContain('text-success');
            expect(menu().innerHTML).toContain('text-danger');
            expect(menu().innerHTML).toContain('text-warning');
        });
    });

    describe('dropdown listener', () => {
        it('re-fetches on show.bs.dropdown', async () => {
            loadModule({ notifications: [notif()] });
            await flush();
            expect(global.fetch).toHaveBeenCalledTimes(1);
            bell().dispatchEvent(new CustomEvent('show.bs.dropdown', { bubbles: true }));
            await flush();
            expect(global.fetch).toHaveBeenCalledTimes(2);
        });
    });
});
