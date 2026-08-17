/* ============================================================================
   Test suite for skydash/static/js/ssh-terminal.js (IIFE module)
   Uses fs.readFileSync + eval in a jsdom environment. The module wires an
   xterm.js terminal to a Socket.IO /ssh namespace; we stub Terminal, io and
   FitAddon BEFORE evaluating so no real network/DOM terminal is touched.
   ============================================================================ */

const fs = require('fs');
const path = require('path');

const SRC_PATH = path.resolve(__dirname, '../skydash/static/js/ssh-terminal.js');

let src;
try {
    src = fs.readFileSync(SRC_PATH, 'utf8');
} catch (e) {
    src = null;
}

/* A minimal xterm.js stand-in that records writes and the registered callbacks. */
function makeFakeTerminal() {
    const term = {
        el: null,
        writeln: jest.fn(),
        write: jest.fn(),
        open: jest.fn((el) => { term.el = el; }),
        loadAddon: jest.fn(),
        fit: jest.fn(),
        onData: jest.fn(),
        onResize: jest.fn(),
    };
    // Capture the handlers xterm would call on data / resize.
    term.onData.mockImplementation((cb) => { term._onData = cb; });
    term.onResize.mockImplementation((cb) => { term._onResize = cb; });
    return term;
}

/* A minimal Socket.IO client stand-in that tracks emits and event handlers. */
function makeFakeSocket() {
    const handlers = {};
    const socket = {
        emit: jest.fn(),
        on: jest.fn((evt, cb) => { handlers[evt] = cb; }),
        _handlers: handlers,
    };
    return socket;
}

describe('ssh-terminal.js IIFE module', () => {
    /* ------------------------------------------------------------------
     * Load the IIFE fresh so every test starts from clean state.
     * ------------------------------------------------------------------ */
    function loadModule(opts = {}) {
        const withLibs = opts.withLibs !== false;

        delete window.SkyDashSSHTerminal;
        delete window.FitAddon;

        // Reset the host element.
        let host = document.getElementById('ssh-host');
        if (host) {
            host.remove();
        }
        if (!opts.noHost) {
            host = document.createElement('div');
            host.id = 'ssh-host';
            document.body.appendChild(host);
        }

        // Stub globals the IIFE references BEFORE evaluating.
        const fakeTerm = makeFakeTerminal();
        const fakeSocket = makeFakeSocket();
        if (withLibs) {
            window.Terminal = jest.fn(() => fakeTerm);
            window.io = jest.fn(() => fakeSocket);
        } else {
            delete window.Terminal;
            delete window.io;
        }

        expect(src).not.toBeNull();
        // eslint-disable-next-line no-eval
        eval(src);

        return { mod: window.SkyDashSSHTerminal, fakeTerm, fakeSocket };
    }

    /* ---- module exposure ---- */
    describe('module exposure', () => {
        it('attaches window.SkyDashSSHTerminal with init', () => {
            const { mod } = loadModule();
            expect(mod).toBeDefined();
            expect(typeof mod.init).toBe('function');
        });
    });

    /* ---- init() guards ---- */
    describe('init() guard behavior', () => {
        it('returns early when the ssh-host element is missing', () => {
            const { mod } = loadModule({ noHost: true });
            mod.init('my-instance');
            expect(window.Terminal).not.toHaveBeenCalled();
            expect(window.io).not.toHaveBeenCalled();
        });

        it('renders loading banner and does not start when libs undefined', () => {
            const host = document.createElement('div');
            host.id = 'ssh-host';
            document.body.appendChild(host);
            delete window.Terminal;
            delete window.io;
            delete window.FitAddon;
            delete window.SkyDashSSHTerminal;
            eval(src);
            window.SkyDashSSHTerminal.init('slug');
            expect(host.innerHTML).toContain('Loading terminal libraries');
            // The CDN bootstrap path must not have opened a socket or terminal.
            expect(document.getElementById('ssh-terminal')).toBeNull();
        });
    });

    /* ---- start() happy path ---- */
    describe('start() wiring', () => {
        let ctx;
        beforeEach(() => { ctx = loadModule(); });

        it('creates a terminal, writes a connect banner and exposes the host div', () => {
            ctx.mod.init('my-instance');
            const host = document.getElementById('ssh-host');
            expect(host.innerHTML).toContain('id="ssh-terminal"');
            expect(window.Terminal).toHaveBeenCalledTimes(1);
            expect(ctx.fakeTerm.open).toHaveBeenCalled();
            expect(ctx.fakeTerm.writeln).toHaveBeenCalledWith('Connecting to SSH session…');
        });

        it('opens the /ssh namespace and emits ssh_open', () => {
            ctx.mod.init('my-instance');
            expect(window.io).toHaveBeenCalledWith('/ssh', { transports: ['websocket', 'polling'] });
            expect(ctx.fakeSocket.emit).toHaveBeenCalledWith('ssh_open', { slug: 'my-instance' });
        });

        it('guards against double-initialisation via the inited flag', () => {
            ctx.mod.init('first');
            ctx.mod.init('second');
            expect(window.Terminal).toHaveBeenCalledTimes(1);
        });

        it('registers ssh_status, ssh_output, onData and onResize handlers', () => {
            ctx.mod.init('my-instance');
            expect(ctx.fakeSocket.on).toHaveBeenCalledWith('ssh_status', expect.any(Function));
            expect(ctx.fakeSocket.on).toHaveBeenCalledWith('ssh_output', expect.any(Function));
            expect(ctx.fakeTerm.onData).toHaveBeenCalledWith(expect.any(Function));
            expect(ctx.fakeTerm.onResize).toHaveBeenCalledWith(expect.any(Function));
        });

        it('emits ssh_input for terminal data and ssh_resize for resize events', () => {
            ctx.mod.init('my-instance');
            ctx.fakeTerm._onData('a');
            expect(ctx.fakeSocket.emit).toHaveBeenCalledWith('ssh_input', { data: 'a' });
            ctx.fakeTerm._onResize({ cols: 80, rows: 24 });
            expect(ctx.fakeSocket.emit).toHaveBeenCalledWith('ssh_resize', { cols: 80, rows: 24 });
        });
    });

    /* ---- ssh_status rendering ---- */
    describe('ssh_status rendering', () => {
        it('writes a green Connected line on success', () => {
            const { mod, fakeTerm, fakeSocket } = loadModule();
            mod.init('my-instance');
            fakeSocket._handlers.ssh_status({ ok: true, host: '10.0.0.5' });
            expect(fakeTerm.writeln).toHaveBeenCalledWith('\x1b[32mConnected to 10.0.0.5\x1b[0m');
        });

        it('writes the error message in red when ok is false', () => {
            const { mod, fakeTerm, fakeSocket } = loadModule();
            mod.init('my-instance');
            fakeSocket._handlers.ssh_status({ ok: false, error: 'session closed' });
            expect(fakeTerm.writeln).toHaveBeenCalledWith('\x1b[31msession closed\x1b[0m');
        });

        it('falls back to Disconnected when ok is false and no error given', () => {
            const { mod, fakeTerm, fakeSocket } = loadModule();
            mod.init('my-instance');
            fakeSocket._handlers.ssh_status({ ok: false });
            expect(fakeTerm.writeln).toHaveBeenCalledWith('\x1b[31mDisconnected\x1b[0m');
        });
    });

    /* ---- ssh_output streaming ---- */
    describe('ssh_output streaming', () => {
        it('writes through stream data to the terminal', () => {
            const { mod, fakeTerm, fakeSocket } = loadModule();
            mod.init('my-instance');
            fakeSocket._handlers.ssh_output({ data: 'hello world' });
            expect(fakeTerm.write).toHaveBeenCalledWith('hello world');
        });

        it('writes an empty string when data is missing', () => {
            const { mod, fakeTerm, fakeSocket } = loadModule();
            mod.init('my-instance');
            fakeSocket._handlers.ssh_output({});
            expect(fakeTerm.write).toHaveBeenCalledWith('');
        });
    });
});
