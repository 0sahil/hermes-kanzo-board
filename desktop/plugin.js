// Kanzo for Hermes Desktop: the user's own Kanzo board as a sidebar page.
//
// The backend (dashboard/plugin_api.py + frame.py) fetches the board's own web UI
// from the running Kanzo and returns it as one document, with a small bridge
// (dashboard/bridge.js) in front of app.js. This page shows that document in the
// SDK's SandboxedFrame and answers the bridge's messages: board requests go to
// the backend proxy, links and copies go through ctx.os, settings into ctx.storage.
import { useQuery, useQueryClient, SandboxedFrame, ErrorState, Skeleton, Button,
  ROUTES_AREA, SIDEBAR_NAV_AREA, PALETTE_AREA, host } from '@hermes/plugin-sdk';
import { useEffect, useMemo, useRef } from 'react';
import { jsx } from 'react/jsx-runtime';

const ID = 'kanzo';
const STORAGE_KEY = 'localStorage';

function toDataUrl(html) {
  const bytes = new TextEncoder().encode(html);
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return 'data:text/html;charset=utf-8;base64,' + btoa(s);
}

function KanzoPage({ ctx }) {
  const qc = useQueryClient();
  const frame = useRef(null);
  const shell = useQuery({
    queryKey: [ID, 'shell'],
    queryFn: () => ctx.rest('/shell', { method: 'POST', body: { storage: ctx.storage.get(STORAGE_KEY, {}) }, timeoutMs: 30000 }),
    staleTime: Infinity, refetchOnWindowFocus: false, retry: 1,
  });
  const src = useMemo(() => (shell.data && shell.data.html ? toDataUrl(shell.data.html) : null), [shell.data]);

  useEffect(() => {
    const onMessage = async e => {
      const win = frame.current && frame.current.contentWindow;
      const d = e.data;
      if (!win || e.source !== win || !d || d.__kz !== 1 || d.reply) return;
      const reply = (value, error) => win.postMessage({ __kz: 1, reply: 1, id: d.id, value, error }, '*');
      try {
        switch (d.type) {
          case 'fetch':
            return reply(await ctx.rest('/proxy', { method: 'POST', body: d.req, timeoutMs: 60000 }));
          case 'storage':
            return ctx.storage.set(STORAGE_KEY, d.data || {});
          case 'copy':
            return reply(await ctx.os.writeClipboard(String(d.text)));
          case 'open':
            if (typeof d.url === 'string' && /^https?:\/\//i.test(d.url)) await ctx.os.openExternal(d.url);
            return;
          case 'version':
            // Kanzo was updated under a cached page: load its new UI.
            if (shell.data && shell.data.version && d.version && d.version !== shell.data.version) {
              qc.invalidateQueries({ queryKey: [ID, 'shell'] });
            }
            return;
        }
      } catch (err) {
        if (d.id) reply(undefined, String((err && err.message) || err || 'Request failed'));
      }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [shell.data]);

  if (shell.isPending) return jsx('div', { className: 'p-6', children: jsx(Skeleton, { className: 'h-64 w-full' }) });
  if (shell.isError || !src) {
    return jsx(ErrorState, {
      title: 'Kanzo board not reachable',
      description: `${(shell.error && shell.error.message) || 'No board page'}. Start the board with \`kanzo\`, or set KANZO_URL in the Hermes .env and restart the gateway.`,
      children: jsx(Button, { variant: 'outline', onClick: () => shell.refetch(), children: 'Retry' }),
    });
  }
  return jsx(SandboxedFrame, {
    ref: frame, src, title: 'Kanzo', sandbox: 'allow-scripts allow-forms allow-downloads',
    style: { position: 'absolute', inset: 0, width: '100%', height: '100%', border: 0, display: 'block' },
  });
}

export default {
  id: ID, name: 'Kanzo', defaultEnabled: true,
  register(ctx) {
    ctx.registerMany([
      { id: 'page', area: ROUTES_AREA, data: { path: '/kanzo' },
        render: () => jsx('div', { style: { position: 'relative', height: '100%', width: '100%' }, children: jsx(KanzoPage, { ctx }) }) },
      { id: 'nav', area: SIDEBAR_NAV_AREA, data: { path: '/kanzo', label: 'Kanzo', codicon: 'project' } },
      { id: 'cmd', area: PALETTE_AREA, data: { label: 'Open Kanzo board', run: () => host.navigate('/kanzo') } },
    ]);
  },
};
