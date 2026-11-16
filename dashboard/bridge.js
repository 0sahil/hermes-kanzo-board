// Runs INSIDE the sandboxed Kanzo frame (inlined by frame.py), before Kanzo's app.js.
// The frame has an opaque origin, so this stands in for what the sandbox removes:
//   fetch('/…')        -> parent (the Hermes plugin) -> plugin backend -> the board
//   localStorage       -> in-frame store, persisted by the plugin
//   confirm()          -> an in-frame dialog (no native modals in the sandbox)
//   links, clipboard   -> opened / copied by the host app
//   location.hostname  -> the board's real host
(function () {
  const cfg = window.__KZ_CFG;
  const BASE = cfg.base;
  window.__KZ_HOST = new URL(BASE).hostname;

  let seq = 0;
  const pending = new Map();
  const send = msg => parent.postMessage(Object.assign({ __kz: 1 }, msg), '*');
  const call = (type, payload) => new Promise((resolve, reject) => {
    const id = ++seq;
    pending.set(id, { resolve, reject });
    send(Object.assign({ type, id }, payload));
  });
  addEventListener('message', e => {
    const d = e.data;
    if (e.source !== parent || !d || !d.__kz || !d.reply) return;
    const p = pending.get(d.id);
    if (!p) return;
    pending.delete(d.id);
    d.error ? p.reject(new TypeError(d.error)) : p.resolve(d.value);
  });

  // localStorage: survives in-frame reloads via window.name, restarts via the plugin.
  let store = cfg.storage || {};
  try { if (window.name.startsWith('kzls:')) store = JSON.parse(window.name.slice(5)); } catch (e) {}
  const persist = () => {
    try { window.name = 'kzls:' + JSON.stringify(store); } catch (e) {}
    send({ type: 'storage', data: store });
  };
  window.__kzStorage = {
    getItem: k => (Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); persist(); },
    removeItem: k => { delete store[k]; persist(); },
    clear: () => { store = {}; persist(); },
    key: i => Object.keys(store)[i] ?? null,
    get length() { return Object.keys(store).length; },
  };

  // fetch('/…') goes through the plugin backend.
  const realFetch = window.fetch.bind(window);
  const toB64 = buf => {
    const u = new Uint8Array(buf);
    let s = '';
    for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
    return btoa(s);
  };
  let versionSent = false;
  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : (input && input.url) || String(input);
    if (!url.startsWith('/') || url.startsWith('//')) return realFetch(input, init);
    const method = (init.method || 'GET').toUpperCase();
    let ctype = new Headers(init.headers || {}).get('content-type');
    let body = init.body, b64 = false;
    if (body instanceof Blob) { ctype = ctype || body.type; body = toB64(await body.arrayBuffer()); b64 = true; }
    else if (body instanceof ArrayBuffer || ArrayBuffer.isView(body)) { body = toB64(body.buffer || body); b64 = true; }
    else if (body != null) body = String(body);
    const r = await call('fetch', { req: { method, path: url, body: body ?? null, b64, ctype } });
    if (r.version && !versionSent) { versionSent = true; send({ type: 'version', version: r.version }); }
    const headers = { 'content-type': r.ctype || 'application/octet-stream' };
    if (r.version) headers['x-kanzo-version'] = r.version;
    const data = r.b64 ? Uint8Array.from(atob(r.body), c => c.charCodeAt(0)) : r.body;
    const empty = [101, 204, 205, 304].includes(r.status);
    return new Response(empty ? null : data, { status: r.status < 200 ? 502 : r.status, headers });
  };

  // Clipboard and history: the sandbox refuses both.
  try {
    Object.defineProperty(navigator, 'clipboard', { configurable: true,
      value: { writeText: text => call('copy', { text }) } });
  } catch (e) {}
  const replaceState = history.replaceState.bind(history);
  history.replaceState = (...a) => { try { replaceState(...a); } catch (e) {} };

  // Links leave through the host app (no popups in the sandbox).
  addEventListener('click', e => {
    if (e.defaultPrevented || e.button !== 0) return;
    const a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    const href = a.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('file:') || href.startsWith('javascript:')) return;
    e.preventDefault();
    send({ type: 'open', url: new URL(href, BASE).href });
  });

  // confirm(): an in-frame dialog styled with Kanzo's own variables.
  window.__kzConfirmSync = () => false;
  window.__kzConfirm = message => new Promise(resolve => {
    const prev = document.activeElement;
    const wrap = document.createElement('div');
    wrap.setAttribute('role', 'dialog');
    wrap.setAttribute('aria-modal', 'true');
    wrap.style.cssText = 'position:fixed;inset:0;z-index:2147483647;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.45)';
    const box = document.createElement('div');
    box.style.cssText = 'background:var(--panel,var(--bg));color:var(--text);border:1px solid var(--border);border-radius:16px;padding:18px 18px 14px;width:min(400px,calc(100vw - 32px));box-shadow:0 12px 40px rgba(0,0,0,.35);font:inherit';
    const text = document.createElement('div');
    text.style.cssText = 'white-space:pre-wrap;line-height:1.45;margin-bottom:16px';
    text.textContent = String(message);
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;justify-content:flex-end;gap:8px';
    const button = (label, primary) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = label;
      b.style.cssText = 'border:0;border-radius:99px;padding:6px 14px;font:inherit;cursor:pointer;' +
        (primary ? 'background:var(--accent);color:var(--accent-text)' : 'background:var(--field,var(--hover));color:var(--text)');
      return b;
    };
    const cancel = button('Cancel', false), ok = button('OK', true);
    const keys = e => {
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); done(false); }
      else if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); done(true); }
      else e.stopPropagation();
    };
    const done = v => {
      wrap.remove();
      removeEventListener('keydown', keys, true);
      try { prev && prev.focus && prev.focus(); } catch (e) {}
      resolve(v);
    };
    cancel.onclick = () => done(false);
    ok.onclick = () => done(true);
    wrap.onclick = e => { if (e.target === wrap) done(false); };
    // A native confirm() swallows the pointer; keep Kanzo's click-outside handlers
    // (e.g. closing the task panel) from seeing clicks on this dialog.
    for (const t of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
      wrap.addEventListener(t, e => e.stopPropagation());
    }
    row.append(cancel, ok);
    box.append(text, row);
    wrap.append(box);
    document.body.append(wrap);
    addEventListener('keydown', keys, true);
    ok.focus();
  });

  // Run app.js: the async-confirm build if it compiles, else the safe fallback.
  window.__kzRun = () => {
    let code = cfg.asyncSource;
    try { new Function(code); } catch (err) {
      console.warn('[kanzo] confirm() transform did not compile; confirm() will cancel:', err);
      code = cfg.syncSource;
    }
    const s = document.createElement('script');
    s.textContent = code;
    document.body.append(s);
  };
})();
