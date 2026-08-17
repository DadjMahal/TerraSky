/* ============================================================================
   Test suite for skydash/static/js/topology.js (IIFE module)
   SVG network topology map rendered into #topology-host from
   window.SKYDASH_INST (public/private IPs + DNS). Uses fs.readFileSync +
   eval in a jsdom environment, mirroring the security-groups suite.
   ============================================================================ */

const fs = require('fs');
const path = require('path');

const SRC_PATH = path.resolve(__dirname, '../skydash/static/js/topology.js');

let src;
try {
    src = fs.readFileSync(SRC_PATH, 'utf8');
} catch (e) {
    src = null;
}

describe('topology.js IIFE module', () => {
    /* Let any pending microtasks settle before inspecting the DOM. The
       module does not auto-fetch (it renders already-present page data),
       but flush() keeps the pattern consistent with sibling suites. */
    function flush() {
        return new Promise((resolve) => setTimeout(resolve, 0));
    }

    /* ------------------------------------------------------------------
     * Load the IIFE fresh for each test so every test starts from a
     * clean state. The module reads window.SKYDASH_INST at render() time,
     * so globals are set *before* eval but can also be mutated afterwards.
     * ------------------------------------------------------------------ */
    function loadModule(opts = {}) {
        const { inst = { name: 'test-inst', provider: 'aws' } } = opts;

        // Set up window globals the IIFE reads at render time.
        delete window.SkyDashTopology;
        if (opts.noInst) {
            delete window.SKYDASH_INST;
        } else {
            window.SKYDASH_INST = inst;
        }

        // Reset the DOM host element.
        let host = document.getElementById('topology-host');
        if (!host) {
            host = document.createElement('div');
            host.id = 'topology-host';
            document.body.appendChild(host);
        } else {
            host.innerHTML = '';
        }

        expect(src).not.toBeNull();
        // eslint-disable-next-line no-eval
        eval(src);

        return window.SkyDashTopology;
    }


    /* ---- exposed API ---- */
    describe('module exposure', () => {
        it('attaches window.SkyDashTopology with a render function', () => {
            const mod = loadModule();
            expect(mod).toBeDefined();
            expect(typeof mod.render).toBe('function');
        });

        it('can be re-evaluated without breaking (no duplicate document listeners)', () => {
            const first = loadModule();
            const second = loadModule();
            expect(first).toBeDefined();
            expect(second).toBeDefined();
            expect(typeof second.render).toBe('function');
            second.render();
            expect(hostHTML()).toContain('topology-svg');
        });
    });

    /* ---- rendering ---- */
    describe('render()', () => {
        it('renders the SVG topology map with nodes and links', () => {
            const mod = loadModule({
                inst: { name: 'web-1', provider: 'aws', public_ip: '1.2.3.4', private_ip: '10.0.0.5', public_dns: 'ec2.example.com' },
            });
            mod.render();

            const host = document.getElementById('topology-host');
            expect(host.innerHTML).toContain('topology-svg');
            // 3 links: Internet->Instance, Instance->Private, Instance->DNS
            expect(host.querySelectorAll('line.link').length).toBe(3);
            // 4 nodes: Internet, Instance (primary), Private, DNS
            expect(host.querySelectorAll('circle.node').length).toBe(4);
            expect(host.querySelectorAll('circle.node-primary').length).toBe(1);
        });

        it('renders the INTERNET, PRIVATE and DNS node labels', () => {
            const mod = loadModule();
            mod.render();
            const html = hostHTML();
            expect(html).toContain('INTERNET');
            expect(html).toContain('PRIVATE');
            expect(html).toContain('DNS');
        });

        it('renders the instance name, provider, and IP/DNS values', () => {
            const mod = loadModule({
                inst: { name: 'web-1', provider: 'aws', public_ip: '1.2.3.4', private_ip: '10.0.0.5', public_dns: 'ec2.example.com' },
            });
            mod.render();
            const html = hostHTML();
            expect(html).toContain('web-1');
            expect(html).toContain('aws');
            expect(html).toContain('1.2.3.4');
            expect(html).toContain('10.0.0.5');
            expect(html).toContain('ec2.example.com');
            // The module renders name (not id) into the SVG label.
            expect(html).not.toContain('instance-id-abc');
        });

        it('renders the "Security groups rendered below" note', () => {
            const mod = loadModule();
            mod.render();
            expect(hostHTML()).toContain('Security groups rendered below');
        });
    });

    function hostHTML() {
        const host = document.getElementById('topology-host');
        return host ? host.innerHTML : '';
    }
/* ---- fallbacks ---- */
    describe('fallbacks', () => {
        it('uses em-dashes (—) for missing public/private IP and DNS', () => {
            const mod = loadModule({ inst: { name: 'bare', provider: 'azure' } });
            mod.render();
            const html = hostHTML();
            expect(html).toContain('—');
            expect(html).not.toContain('undefined');
        });

        it('renders an empty name and provider when they are absent', () => {
            const mod = loadModule({ inst: {} });
            mod.render();
            const html = hostHTML();
            expect(html).not.toContain('undefined');
            expect(html).toContain('topology-svg');
        });

        it('renders without throwing when window.SKYDASH_INST is missing', () => {
            const mod = loadModule({ noInst: true });
            expect(() => mod.render()).not.toThrow();
            const html = hostHTML();
            expect(html).toContain('topology-svg');
            expect(html).toContain('—');
            expect(html).not.toContain('undefined');
        });
    });

    /* ---- name truncation ---- */
    describe('name truncation', () => {
        it('truncates a long instance name to 14 characters', () => {
            const mod = loadModule({ inst: { name: 'a-very-long-instance-name-that-exceeds-14', provider: 'oracle' } });
            mod.render();
            expect(hostHTML()).toContain('a-very-long-in');
            expect(hostHTML()).not.toContain('a-very-long-instance-name-that-exceeds-14');
        });

        it('keeps short names intact', () => {
            const mod = loadModule({ inst: { name: 'web-1', provider: 'aws' } });
            mod.render();
            expect(hostHTML()).toContain('web-1');
        });
    });

    /* ---- missing host element ---- */
    describe('missing host element', () => {
        it('no-ops silently when #topology-host does not exist', () => {
            const mod = loadModule({ noInst: true });
            // loadModule re-creates the host, so remove it again to test no-op.
            document.getElementById('topology-host').remove();
            expect(() => mod.render()).not.toThrow();
            expect(document.getElementById('topology-host')).toBeNull();
        });
    });

    /* ---- re-render idempotency ---- */
    describe('re-render', () => {
        it('replaces previous output when render is called again', async () => {
            const mod = loadModule({ inst: { name: 'v1', provider: 'aws', public_ip: '1.1.1.1' } });
            mod.render();
            expect(hostHTML()).toContain('v1');

            window.SKYDASH_INST = { name: 'v2', provider: 'azure', public_ip: '2.2.2.2' };
            await flush();
            mod.render();
            const html = hostHTML();
            expect(html).toContain('v2');
            expect(html).toContain('2.2.2.2');
            expect(html).not.toContain('1.1.1.1');
        });
    });
});
