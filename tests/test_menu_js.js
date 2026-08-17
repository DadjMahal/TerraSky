/* ============================================================================
   Test suite for skydash/static/js/menu.js (sidebar toggle IIFE module)
   Uses fs.readFileSync + eval in a jsdom environment.
   ============================================================================ */

const fs = require('fs');
const path = require('path');

const SRC_PATH = path.resolve(__dirname, '../skydash/static/js/menu.js');

let src;
try {
    src = fs.readFileSync(SRC_PATH, 'utf8');
} catch (e) {
    src = null;
}

function flush() {
    return new Promise((resolve) => setTimeout(resolve, 0));
}

describe('menu.js IIFE module', () => {
    function loadModule(opts = {}) {
        const matches = opts.matches !== undefined ? opts.matches : true; // desktop by default

        delete window.SkyDashSidebar;
        localStorage.clear();

        // The IIFE calls window.matchMedia at load time, so mock it up first.
        const mql = {
            matches,
            media: '(min-width: 768px)',
            addEventListener: jest.fn(),
            removeEventListener: jest.fn(),
            addListener: jest.fn(),
            removeListener: jest.fn(),
            onchange: null,
            dispatchEvent: jest.fn(),
        };
        window.matchMedia = jest.fn(() => mql);

        document.body.innerHTML =
            '<div id="skydash-sidebar"></div>' +
            '<button id="sidebar-toggle-btn"></button>' +
            '<button id="map-toggle"></button>' +
            '<a data-map-toggle href="#"></a>';

        if (opts.preloadStorage !== undefined) {
            localStorage.setItem('skydash-sidebar-collapsed', opts.preloadStorage);
        }

        expect(src).not.toBeNull();
        // eslint-disable-next-line no-eval
        eval(src);

        return { mod: window.SkyDashSidebar, mql };
    }

    const sidebar = () => document.getElementById('skydash-sidebar');

    describe('restore persisted state on load', () => {
        it('collapses the sidebar when localStorage stores "1"', () => {
            loadModule({ preloadStorage: '1' });
            expect(sidebar().classList.contains('collapsed')).toBe(true);
            expect(document.body.classList.contains('sidebar-collapsed')).toBe(true);
            expect(toggleBtn().getAttribute('aria-label')).toBe('Expand sidebar');
        });

        it('keeps sidebar expanded when localStorage is empty', () => {
            loadModule();
            expect(sidebar().classList.contains('collapsed')).toBe(false);
            expect(toggleBtn().getAttribute('aria-label')).toBe('Collapse sidebar');
        });
    });

    describe('toggle button (desktop)', () => {
        it('collapses on first click and persists state', () => {
            const { mql } = loadModule({ matches: true });
            expect(mql.addEventListener).toHaveBeenCalled();
            toggleBtn().click();
            expect(sidebar().classList.contains('collapsed')).toBe(true);
            expect(document.body.classList.contains('sidebar-collapsed')).toBe(true);
            expect(localStorage.getItem('skydash-sidebar-collapsed')).toBe('1');
            expect(toggleBtn().getAttribute('aria-label')).toBe('Expand sidebar');
        });

        it('expands on second click', () => {
            loadModule({ preloadStorage: '1', matches: true });
            toggleBtn().click();
            expect(sidebar().classList.contains('collapsed')).toBe(false);
            expect(localStorage.getItem('skydash-sidebar-collapsed')).toBe('0');
        });
    });

    const toggleBtn = () => document.getElementById('sidebar-toggle-btn');

    describe('module exposure', () => {
        it('exposes collapse, expand, toggle and isCollapsed', () => {
            const { mod } = loadModule();
            expect(typeof mod.collapse).toBe('function');
            expect(typeof mod.expand).toBe('function');
            expect(typeof mod.toggle).toBe('function');
            expect(typeof mod.isCollapsed).toBe('function');
        });
    });

    describe('toggle button (mobile)', () => {
        it('toggles the show class for the drawer', () => {
            loadModule({ matches: false });
            expect(sidebar().classList.contains('show')).toBe(false);
            toggleBtn().click();
            expect(sidebar().classList.contains('show')).toBe(true);
            toggleBtn().click();
            expect(sidebar().classList.contains('show')).toBe(false);
        });

        it('does not toggle collapsed on mobile', () => {
            const { mod } = loadModule({ matches: false });
            mod.toggle();
            expect(sidebar().classList.contains('collapsed')).toBe(false);
        });
    });

    describe('API collapse/expand/toggle/isCollapsed', () => {
        it('collapse() and expand() update classes and storage', () => {
            const { mod } = loadModule();
            mod.expand();
            expect(sidebar().classList.contains('collapsed')).toBe(false);
            mod.collapse();
            expect(sidebar().classList.contains('collapsed')).toBe(true);
            expect(mod.isCollapsed()).toBe(true);
            expect(localStorage.getItem('skydash-sidebar-collapsed')).toBe('1');
        });

        it('isCollapsed reflects persisted state', () => {
            const { mod } = loadModule({ preloadStorage: '1' });
            expect(mod.isCollapsed()).toBe(true);
        });
    });

    describe('Escape key closes mobile drawer', () => {
        it('removes the show class on Escape', () => {
            loadModule({ matches: false });
            toggleBtn().click();
            expect(sidebar().classList.contains('show')).toBe(true);
            document.dispatchEvent(
                new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
            );
            expect(sidebar().classList.contains('show')).toBe(false);
        });
    });

    describe('map region toggle', () => {
        it('clicks #map-toggle when a data-map-toggle link is clicked', () => {
            loadModule();
            const mapToggle = document.getElementById('map-toggle');
            let clicked = false;
            mapToggle.addEventListener('click', () => { clicked = true; });
            const link = document.querySelector('[data-map-toggle]');
            link.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
            expect(clicked).toBe(true);
        });
    });

    describe('missing elements', () => {
        it('returns early without error when sidebar/toggle are absent', () => {
            document.body.innerHTML = '<div></div>';
            delete window.SkyDashSidebar;
            expect(() => { eval(src); }).not.toThrow();
            expect(window.SkyDashSidebar).toBeUndefined();
        });
    });
});
