/* Test suite for skydash/static/js/file-manager.js (IIFE module). */
const fs = require('fs');
const path = require('path');
const SRC_PATH = path.resolve(__dirname, '../skydash/static/js/file-manager.js');
let src;
try { src = fs.readFileSync(SRC_PATH, 'utf8'); } catch (e) { src = null; }

describe('file-manager.js IIFE module', () => {
  beforeEach(() => { global.fetch = jest.fn(); });

  function loadModule(opts = {}) {
    const slug = opts.slug !== undefined ? opts.slug : 'my-instance';
    const dispatchDOMContentLoaded = opts.dispatchDOMContentLoaded !== false;
    delete window.SkyDashFileManager;
    window.SKYDASH_SLUG = slug;
    window.SKYDASH_INST = opts.inst || {};
    document.body.innerHTML =
      '<div id="fm-listing"></div><div id="fm-tree"></div>' +
      '<div id="fm-breadcrumb"></div><div id="fm-disk"></div>';
    global.fetch.mockReset();
    global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({ status: 'ok', data: {} }) });
    expect(src).not.toBeNull();
    eval(src);
    if (dispatchDOMContentLoaded) {
      document.dispatchEvent(new Event('DOMContentLoaded'));
    }
    return window.SkyDashFileManager;
  }
  const flush = () => new Promise(r => setTimeout(r, 30));
  const listing = () => document.getElementById('fm-listing').innerHTML;
  const disk = () => document.getElementById('fm-disk').innerHTML;
  const bc = () => document.getElementById('fm-breadcrumb').innerHTML;

  describe('module exposure', () => {
    it('exposes init, navigate and showToast', () => {
      const mod = loadModule();
      expect(typeof mod.init).toBe('function');
      expect(typeof mod.navigate).toBe('function');
      expect(typeof mod.showToast).toBe('function');
    });
  });

  describe('init()', () => {
    it('returns early when SKYDASH_SLUG is falsy', () => {
      const mod = loadModule({ slug: '', dispatchDOMContentLoaded: false });
      mod.init();
      expect(global.fetch).not.toHaveBeenCalled();
    });
    it('renders listing and disk when slug is present', async () => {
      const mod = loadModule();
      mod.init();
      await flush();
      expect(global.fetch).toHaveBeenCalled();
      expect(listing()).toContain('Directory is empty.');
    });
  });

  describe('fetchLs() via navigate', () => {
    it('renders file entries on a 200 response', async () => {
      loadModule();
      global.fetch.mockResolvedValue({
        ok: true, status: 200,
        json: async () => ({ status: 'ok', data: { entries: [{ name: 'file.txt', path: '/file.txt', type: 'file', size: 100 }] } })
      });
      window.SkyDashFileManager.navigate('/');
      await flush();
      expect(listing()).toContain('file.txt');
      expect(listing()).toContain('fm-table');
    });
    it('shows authentication error on 401', async () => {
      loadModule();
      global.fetch.mockResolvedValue({ ok: false, status: 401, json: async () => ({}) });
      window.SkyDashFileManager.navigate('/');
      await flush();
      expect(listing()).toContain('alert-warning');
      expect(listing()).toContain('Authentication required.');
    });
    it('passes provider error message on 502', async () => {
      loadModule();
      global.fetch.mockResolvedValue({ ok: false, status: 502, json: async () => ({ error: 'SFTP provider offline' }) });
      window.SkyDashFileManager.navigate('/');
      await flush();
      expect(listing()).toContain('SFTP provider offline');
    });
    it('shows default provider message on 502 without api error', async () => {
      loadModule();
      global.fetch.mockResolvedValue({ ok: false, status: 502, json: async () => ({}) });
      window.SkyDashFileManager.navigate('/');
      await flush();
      expect(listing()).toContain('Provider error.');
    });
    it('escapes HTML in error messages', async () => {
      loadModule();
      global.fetch.mockResolvedValue({ ok: false, status: 500, json: async () => ({ error: '<script>alert(1)</script>' }) });
      window.SkyDashFileManager.navigate('/');
      await flush();
      expect(listing()).toContain('&lt;script&gt;');
      expect(listing()).not.toContain('<script>');
    });
    it('shows the error message when fetch rejects', async () => {
      loadModule();
      global.fetch.mockRejectedValue(new Error('Network failure'));
      window.SkyDashFileManager.navigate('/');
      await flush();
      expect(listing()).toContain('alert-warning');
      expect(listing()).toContain('Network failure');
    });
  });

  describe('renderListing()', () => {
    it('shows empty directory message', async () => {
      loadModule();
      global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({ status: 'ok', data: { entries: [] } }) });
      window.SkyDashFileManager.navigate('/');
      await flush();
      expect(listing()).toContain('Directory is empty.');
    });
    it('formats file size with fmtSize', async () => {
      loadModule();
      global.fetch.mockResolvedValue({
        ok: true, status: 200,
        json: async () => ({ status: 'ok', data: { entries: [{ name: 'file.bin', path: '/file.bin', type: 'file', size: 2048 }] } })
      });
      window.SkyDashFileManager.navigate('/');
      await flush();
      expect(listing()).toContain('2.0 KB');
    });
  });

  describe('navigate() and breadcrumb', () => {
    it('renders root slash breadcrumb for "/"', async () => {
      loadModule();
      global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({ status: 'ok', data: { entries: [] } }) });
      window.SkyDashFileManager.navigate('/');
      await flush();
      expect(bc()).toContain('Home');
      expect(bc()).toContain('data-path="/"');
    });
    it('renders nested crumbs for a subdirectory', async () => {
      loadModule();
      global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({ status: 'ok', data: { entries: [] } }) });
      window.SkyDashFileManager.navigate('/home/user/');
      await flush();
      expect(bc()).toContain('Home');
      expect(bc()).toContain('home');
      expect(bc()).toContain('user');
      expect(bc()).toContain('data-path="/home/"');
      expect(bc()).toContain('data-path="/home/user/"');
    });
  });

  describe('renderDisk()', () => {
    it('renders disk usage when total is present', async () => {
      loadModule();
      global.fetch.mockImplementation((url) => {
        if (String(url).includes('/disk')) {
          return Promise.resolve({ ok: true, status: 200, json: async () => ({ status: 'ok', data: { used: 512000000, total: 1024000000, percent_used: 50 } }) });
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => ({ status: 'ok', data: { entries: [] } }) });
      });
      window.SkyDashFileManager.navigate('/');
      await flush();
      expect(disk()).toContain('Disk:');
      expect(disk()).toContain('(50%)');
    });
    it('leaves disk empty when total is undefined', async () => {
      loadModule();
      global.fetch.mockImplementation((url) => {
        if (String(url).includes('/disk')) {
          return Promise.resolve({ ok: true, status: 200, json: async () => ({ status: 'ok', data: {} }) });
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => ({ status: 'ok', data: { entries: [] } }) });
      });
      window.SkyDashFileManager.navigate('/');
      await flush();
      expect(disk()).toBe('');
    });
  });

  describe('iconFor()', () => {
    const lsEntry = (entry) => { loadModule(); global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({ status: 'ok', data: { entries: [entry] } }) }); window.SkyDashFileManager.navigate('/'); return flush(); };

    it('uses folder icon for directories', async () => {
      await lsEntry({ name: 'mydir', path: '/mydir', type: 'dir' });
      expect(listing()).toContain('bi-folder2-open');
    });
    it('uses js icon for .js files', async () => {
      await lsEntry({ name: 'app.js', path: '/app.js', type: 'file', size: 100 });
      expect(listing()).toContain('bi-filetype-js');
    });
    it('falls back to generic icon for unknown extensions', async () => {
      await lsEntry({ name: 'data.xyz', path: '/data.xyz', type: 'file', size: 100 });
      expect(listing()).toContain('bi-file-earmark');
    });
  });

  describe('showToast()', () => {
    it('delegates to SkyDashDetail.showToast when available', () => {
      window.SkyDashDetail = { showToast: jest.fn() };
      const mod = loadModule();
      mod.showToast('Saved', true);
      expect(window.SkyDashDetail.showToast).toHaveBeenCalledWith('Saved', true);
      delete window.SkyDashDetail;
    });
  });

  describe('shown.bs.tab listener', () => {
    it('calls init when the files tab is shown', () => {
      loadModule();
      const target = document.createElement('div');
      target.getAttribute = (attr) => (attr === 'href' ? '#tab-files' : null);
      document.body.appendChild(target);
      target.dispatchEvent(new CustomEvent('shown.bs.tab', { bubbles: true }));
      expect(global.fetch).toHaveBeenCalled();
    });
  });
});
