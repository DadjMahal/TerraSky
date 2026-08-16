/* ============================================================================
   Test suite for skydash/static/js/security-groups.js (IIFE module)
   Uses fs.readFileSync + eval in a jsdom environment.
   ============================================================================ */

const fs = require('fs');
const path = require('path');

const SRC_PATH = path.resolve(__dirname, '../skydash/static/js/security-groups.js');

let src;
try {
    src = fs.readFileSync(SRC_PATH, 'utf8');
} catch (e) {
    src = null;
}

describe('security-groups.js IIFE module', () => {
    beforeEach(() => {
        global.fetch = jest.fn();
    });

    /* ------------------------------------------------------------------
     * Load the IIFE fresh for each test so every test starts from clean state.
     * ------------------------------------------------------------------ */
    function loadModule(opts = {}) {
        const { slug = 'my-instance', inst = { provider_label: 'aws' }, csrf = 'tok-123' } = opts;

        // Set up window globals the IIFE expects.
        delete window.SkyDashSecurityGroups;
        window.SKYDASH_SLUG = slug;
        window.SKYDASH_INST = inst;
        window.CSRF_TOKEN = csrf;

        // The IIFE reads document.readyState at load time.
        Object.defineProperty(document, 'readyState', {
            configurable: true,
            value: opts.readyState || 'complete',
            writable: true,
        });

        // Reset the DOM host element.
        let host = document.getElementById('security-groups-host');
        if (!host) {
            host = document.createElement('div');
            host.id = 'security-groups-host';
            document.body.appendChild(host);
        } else {
            host.innerHTML = '';
        }

        // Reset the badge element.
        let badge = document.getElementById('sg-provider-badge');
        if (!badge) {
            badge = document.createElement('div');
            badge.id = 'sg-provider-badge';
            document.body.appendChild(badge);
        } else {
            badge.textContent = '';
        }

        // Reset fetch mock.
        global.fetch.mockReset();
        global.fetch.mockResolvedValue({
            ok: true,
            status: 200,
            json: async () => ({ status: 'ok', data: [] }),
        });

        expect(src).not.toBeNull();
        // eslint-disable-next-line no-eval
        eval(src);

        return window.SkyDashSecurityGroups;
    }

    /* ---- exposed API ---- */
    describe('module exposure', () => {
        it('attaches window.SkyDashSecurityGroups with fetch and render', () => {
            const mod = loadModule();
            expect(mod).toBeDefined();
            expect(typeof mod.fetch).toBe('function');
            expect(typeof mod.render).toBe('function');
        });
    });

    /* ---- init behavior ---- */
    describe('init()', () => {
        it('sets the provider badge text from SKYDASH_INST.provider_label', () => {
            loadModule({ inst: { provider_label: 'Oracle Cloud' } });
            const badge = document.getElementById('sg-provider-badge');
            expect(badge.textContent).toBe('Oracle Cloud');
        });

        it('does not set badge text when provider_label is missing', () => {
            loadModule({ inst: {} });
            const badge = document.getElementById('sg-provider-badge');
            expect(badge.textContent).toBe('');
        });

        it('does not set badge text when INST has no provider_label', () => {
            loadModule({ inst: { provider: 'aws' } });
            const badge = document.getElementById('sg-provider-badge');
            expect(badge.textContent).toBe('');
        });

        it('fetches security groups on load (readyState complete)', () => {
            loadModule();
            expect(global.fetch).toHaveBeenCalledTimes(1);
            const [url, opts] = global.fetch.mock.calls[0];
            expect(url).toBe('/api/v1/instance/my-instance/security-groups');
            expect(opts.headers['X-CSRF-Token']).toBe('tok-123');
        });

        it('defers init until DOMContentLoaded when readyState is loading', () => {
            loadModule({ readyState: 'loading' });
            expect(global.fetch).not.toHaveBeenCalled();

            document.dispatchEvent(new Event('DOMContentLoaded'));
            expect(global.fetch).toHaveBeenCalledTimes(1);
        });

        it('uses empty string for CSRF token when window.CSRF_TOKEN is absent', () => {
            global.fetch.mockReset();
            delete window.CSRF_TOKEN;
            Object.defineProperty(document, 'readyState', {
                configurable: true,
                value: 'complete',
                writable: true,
            });
            let host = document.getElementById('security-groups-host');
            if (!host) {
                host = document.createElement('div');
                host.id = 'security-groups-host';
                document.body.appendChild(host);
            }
            host.innerHTML = '';
            let badge = document.getElementById('sg-provider-badge');
            if (!badge) {
                badge = document.createElement('div');
                badge.id = 'sg-provider-badge';
                document.body.appendChild(badge);
            } else {
                badge.textContent = '';
            }
            delete window.SkyDashSecurityGroups;
            window.SKYDASH_SLUG = 'test-inst';
            window.SKYDASH_INST = {};

            // eslint-disable-next-line no-eval
            eval(src);

            expect(global.fetch).toHaveBeenCalledTimes(1);
            const [, opts] = global.fetch.mock.calls[0];
            expect(opts.headers['X-CSRF-Token']).toBe('');
        });
    });

    /* ---- shown.bs.tab re-fetch ---- */
    describe('shown.bs.tab listener', () => {
        it('does not re-fetch for non-network tabs', () => {
            loadModule();
            global.fetch.mockClear();

            const evt = new Event('shown.bs.tab');
            evt.target = null;
            document.dispatchEvent(evt);

            expect(global.fetch).not.toHaveBeenCalled();
        });

        it('re-fetches when tab-network is targeted via data-bs-target', () => {
            loadModule();
            global.fetch.mockClear();

            const target = document.createElement('button');
            target.setAttribute('data-bs-target', '#tab-network');

            const evt = new Event('shown.bs.tab');
            evt.target = target;
            document.dispatchEvent(evt);

            expect(global.fetch).toHaveBeenCalledTimes(1);
        });

        it('re-fetches when tab-network is targeted via href', () => {
            loadModule();
            global.fetch.mockClear();

            const target = document.createElement('a');
            target.setAttribute('href', '#tab-network');

            const evt = new Event('shown.bs.tab');
            evt.target = target;
            document.dispatchEvent(evt);

            expect(global.fetch).toHaveBeenCalledTimes(1);
        });

        it('ignores tabs that are not the network tab', () => {
            loadModule();
            global.fetch.mockClear();

            const target = document.createElement('button');
            target.setAttribute('data-bs-target', '#tab-other');

            const evt = new Event('shown.bs.tab');
            evt.target = target;
            document.dispatchEvent(evt);

            expect(global.fetch).not.toHaveBeenCalled();
        });
    });

    /* ---- fetchSecurityGroups error paths ---- */
    describe('fetchSecurityGroups() error handling', () => {
        it('handles 401 with authentication error message', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockResolvedValue({
                ok: false,
                status: 401,
                json: async () => ({ status: 'error' }),
            });

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('Authentication required to view security groups.');
            expect(host.innerHTML).toContain('bi bi-exclamation-triangle');
        });

        it('handles 503 with provider credentials unavailable message', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockResolvedValue({
                ok: false,
                status: 503,
                json: async () => ({}),
            });

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('Provider credentials unavailable; security groups cannot be fetched.');
        });

        it('handles 502 with provider error message', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockResolvedValue({
                ok: false,
                status: 502,
                json: async () => ({}),
            });

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('Provider error while fetching security groups.');
        });

        it('handles 403 (generic non-ok) with HTTP status message', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockResolvedValue({
                ok: false,
                status: 403,
                json: async () => ({ error: 'forbidden' }),
            });

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('Failed to fetch security groups (HTTP 403).');
        });

        it('handles 404 with HTTP status message', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockResolvedValue({
                ok: false,
                status: 404,
                json: async () => ({}),
            });

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('Failed to fetch security groups (HTTP 404).');
        });

        it('handles 500 with HTTP status message', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockResolvedValue({
                ok: false,
                status: 500,
                json: async () => ({}),
            });

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('Failed to fetch security groups (HTTP 500).');
        });

        it('handles 404 with HTTP status message', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockResolvedValue({
                ok: false,
                status: 504,
                json: async () => ({}),
            });

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('Failed to fetch security groups (HTTP 504).');
        });

        it('handles network errors in the catch block', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockRejectedValue(new Error('ECONNREFUSED'));

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('Error: ECONNREFUSED');
        });

        it('handles network errors with no message', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockRejectedValue({});

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('Error: network failure');
        });

        it('handles rejected promise with null error', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockRejectedValue(null);

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('Error: network failure');
        });
    });

    /* ---- fetchSecurityGroups success path ---- */
    describe('fetchSecurityGroups() success', () => {
        it('renders groups from payload.data when status is "ok"', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockResolvedValue({
                ok: true,
                status: 200,
                json: async () => ({
                    status: 'ok',
                    data: [{
                        name: 'sg-primary',
                        id: 'sg-123',
                        provider: 'aws',
                        type: 'Security Group',
                        inbound: [{ protocol: 'tcp', port: '22', source: '0.0.0.0/0', action: 'allow', description: 'SSH access' }],
                        outbound: [{ protocol: 'all', port: 'all', source: '0.0.0.0/0', action: 'allow', description: 'Internet access' }],
                    }],
                }),
            });

            await mod.fetch();

            expect(global.fetch).toHaveBeenCalledWith(
                '/api/v1/instance/my-instance/security-groups',
                { headers: { 'X-CSRF-Token': 'tok-123' } }
            );

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('sg-primary');
            expect(host.innerHTML).toContain('sg-123');
            expect(host.innerHTML).toContain('aws');
            expect(host.innerHTML).toContain('Security Group');
            expect(host.innerHTML).toContain('Inbound');
            expect(host.innerHTML).toContain('Outbound');
            expect(host.innerHTML).toContain('SSH access');
            expect(host.innerHTML).toContain('Internet access');
            expect(host.innerHTML).toContain('#FF9900');
        });

        it('renders groups from payload.groups when status is not "ok"', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockResolvedValue({
                ok: true,
                status: 200,
                json: async () => ({
                    status: 'partial',
                    groups: [{
                        name: 'fw-east',
                        id: 'fw-456',
                        provider: 'azure',
                        type: 'Firewall',
                        inbound: [],
                        outbound: [],
                    }],
                }),
            });

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('fw-east');
            expect(host.innerHTML).toContain('fw-456');
            expect(host.innerHTML).toContain('azure');
            expect(host.innerHTML).toContain('Firewall');
        });

        it('renders empty state when payload.data is empty array', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockResolvedValue({
                ok: true,
                status: 200,
                json: async () => ({ status: 'ok', data: [] }),
            });

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('No security groups or firewalls found for this instance.');
        });

        it('renders empty state when payload has no groups or data', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockResolvedValue({
                ok: true,
                status: 200,
                json: async () => ({ status: 'ok' }),
            });

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('No security groups or firewalls found for this instance.');
        });

        it('renders fallback when status is not "ok" and no groups key', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockResolvedValue({
                ok: true,
                status: 200,
                json: async () => ({ status: 'error', someOtherKey: 'value' }),
            });

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('No security groups or firewalls found for this instance.');
        });

        it('encodes the slug in the URL', async () => {
            const mod = loadModule({ slug: 'my instance/slug' });
            await mod.fetch();
            expect(global.fetch).toHaveBeenCalledWith(
                '/api/v1/instance/my%20instance%2Fslug/security-groups',
                expect.any(Object)
            );
        });
    });

    /* ---- render() directly ---- */
    describe('render()', () => {
        it('renders multiple security groups', () => {
            const mod = loadModule();
            const groups = [
                { name: 'sg-1', id: 'id-1', provider: 'aws', type: 'Security Group', inbound: [], outbound: [] },
                { name: 'fw-1', id: 'id-2', provider: 'azure', type: 'Firewall', inbound: [], outbound: [] },
                { name: 'sg-2', id: 'id-3', provider: 'gcp', type: 'Security Group', inbound: [], outbound: [] },
            ];
            mod.render(groups);
            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('sg-1');
            expect(host.innerHTML).toContain('fw-1');
            expect(host.innerHTML).toContain('sg-2');
            expect(host.innerHTML).toContain('#FF9900');
            expect(host.innerHTML).toContain('#0078D4');
            expect(host.innerHTML).toContain('#6c757d');
        });

        it('renders empty state when groups is null', () => {
            const mod = loadModule();
            mod.render(null);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('No security groups or firewalls found for this instance.');
        });

        it('renders empty state when groups is empty array', () => {
            const mod = loadModule();
            mod.render([]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('No security groups or firewalls found for this instance.');
        });

        it('renders empty state when groups is undefined', () => {
            const mod = loadModule();
            mod.render(undefined);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('No security groups or firewalls found for this instance.');
        });

        it('does nothing when host element is missing', () => {
            const mod = loadModule();
            document.getElementById('security-groups-host').remove();
            expect(() => mod.render([{ name: 'sg', id: 'id', provider: 'aws', inbound: [], outbound: [] }])).not.toThrow();
        });

        it('falls back to sg.id when sg.name is missing', () => {
            const mod = loadModule();
            mod.render([{ id: 'sg-fallback', provider: 'aws', inbound: [], outbound: [] }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('sg-fallback');
        });

        it('falls back to "Security Group" when type is missing', () => {
            const mod = loadModule();
            mod.render([{ name: 'sg-notype', id: 'id', provider: 'aws', inbound: [], outbound: [] }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('Security Group');
        });
    });

    /* ---- ruleRow / renderTable behavior ---- */
    describe('ruleRow rendering', () => {
        it('renders deny action with text-danger class', () => {
            const mod = loadModule();
            mod.render([{
                name: 'sg-test', id: 'id', provider: 'aws',
                inbound: [{ protocol: 'tcp', port: '80', source: '10.0.0.0/8', action: 'deny', description: 'Block HTTP' }],
                outbound: [],
            }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('text-danger');
        });

        it('renders allow action with text-success class', () => {
            const mod = loadModule();
            mod.render([{
                name: 'sg-test', id: 'id', provider: 'aws',
                inbound: [{ protocol: 'tcp', port: '443', source: '0.0.0.0/0', action: 'allow', description: 'HTTPS' }],
                outbound: [],
            }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('text-success');
        });

        it('defaults port to "all" when not specified', () => {
            const mod = loadModule();
            mod.render([{
                name: 'sg-test', id: 'id', provider: 'aws',
                inbound: [{ protocol: 'icmp', source: '0.0.0.0/0', action: 'allow', description: 'Ping' }],
                outbound: [],
            }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('all');
        });

        it('defaults source to "0.0.0.0/0" when not specified', () => {
            const mod = loadModule();
            mod.render([{
                name: 'sg-test', id: 'id', provider: 'aws',
                inbound: [{ protocol: 'tcp', port: '22', action: 'allow', description: 'SSH' }],
                outbound: [],
            }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('0.0.0.0/0');
        });

        it('defaults action to "allow" when not specified', () => {
            const mod = loadModule();
            mod.render([{
                name: 'sg-test', id: 'id', provider: 'aws',
                inbound: [{ protocol: 'tcp', port: '22', source: '0.0.0.0/0', description: 'SSH' }],
                outbound: [],
            }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('text-success');
        });

        it('renders "No rules in this policy." for empty inbound rules', () => {
            const mod = loadModule();
            mod.render([{
                name: 'sg-test', id: 'id', provider: 'aws',
                inbound: [],
                outbound: [{ protocol: 'tcp', port: '443', source: '0.0.0.0/0', action: 'allow', description: 'HTTPS' }],
            }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('No rules in this policy.');
        });

        it('renders "No rules in this policy." for empty outbound rules', () => {
            const mod = loadModule();
            mod.render([{
                name: 'sg-test', id: 'id', provider: 'aws',
                inbound: [{ protocol: 'tcp', port: '22', source: '0.0.0.0/0', action: 'allow', description: 'SSH' }],
                outbound: [],
            }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('No rules in this policy.');
        });
    });

    /* ---- escaping ---- */
    describe('HTML escaping', () => {
        it('escapes special characters in rule fields', () => {
            const mod = loadModule();
            mod.render([{
                name: 'sg-test', id: 'id', provider: 'aws',
                inbound: [{
                    protocol: 'tcp<script>&"',
                    port: '80',
                    source: '0.0.0.0/0',
                    action: 'allow',
                    description: 'desc <b>& "test"',
                }],
                outbound: [],
            }]);
            const html = document.getElementById('security-groups-host').innerHTML;
            expect(html).not.toContain('<script>');
            expect(html).toContain('&lt;script&gt;');
            expect(html).toContain('&amp;');
            expect(html).toContain('&quot;');
        });

        it('escapes special characters in group name', () => {
            const mod = loadModule();
            mod.render([{
                name: 'sg<weird>&name"',
                id: 'id',
                provider: 'aws',
                inbound: [],
                outbound: [],
            }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('sg&lt;weird&gt;&amp;name&quot;');
        });

        it('escapes special characters in provider', () => {
            const mod = loadModule();
            mod.render([{
                name: 'sg-test', id: 'id', provider: 'custom<"&>',
                inbound: [],
                outbound: [],
            }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('custom&lt;');
        });
    });

    /* ---- provider color mapping ---- */
    describe('provider colors', () => {
        it('renders AWS color (#FF9900)', () => {
            const mod = loadModule();
            mod.render([{ name: 'aws-sg', id: 'id', provider: 'aws', inbound: [], outbound: [] }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('#FF9900');
        });

        it('renders Azure color (#0078D4)', () => {
            const mod = loadModule();
            mod.render([{ name: 'azure-sg', id: 'id', provider: 'azure', inbound: [], outbound: [] }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('#0078D4');
        });

        it('renders Oracle color (#F80000)', () => {
            const mod = loadModule();
            mod.render([{ name: 'oracle-sg', id: 'id', provider: 'oracle', inbound: [], outbound: [] }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('#F80000');
        });

        it('renders Alibaba color (#FF6A00)', () => {
            const mod = loadModule();
            mod.render([{ name: 'alibaba-sg', id: 'id', provider: 'alibaba', inbound: [], outbound: [] }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('#FF6A00');
        });

        it('renders DigitalOcean color (#0080FF)', () => {
            const mod = loadModule();
            mod.render([{ name: 'do-sg', id: 'id', provider: 'digitalocean', inbound: [], outbound: [] }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('#0080FF');
        });

        it('defaults to #6c757d for unknown providers', () => {
            const mod = loadModule();
            mod.render([{ name: 'unknown-sg', id: 'id', provider: 'rackspace', inbound: [], outbound: [] }]);
            expect(document.getElementById('security-groups-host').innerHTML).toContain('#6c757d');
        });
    });

    /* ---- showError ---- */
    describe('showError()', () => {
        it('renders error message with warning alert and icon', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockRejectedValue(new Error('custom error'));

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).toContain('alert-warning');
            expect(host.innerHTML).toContain('bi bi-exclamation-triangle');
        });

        it('escapes error message in showError', async () => {
            const mod = loadModule();
            global.fetch.mockReset();
            global.fetch.mockRejectedValue(new Error('<script>alert(1)</script>'));

            await mod.fetch();

            const host = document.getElementById('security-groups-host');
            expect(host.innerHTML).not.toContain('<script>alert(1)</script>');
            expect(host.innerHTML).toContain('&lt;script&gt;');
        });
    });
});
