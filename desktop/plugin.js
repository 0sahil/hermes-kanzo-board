// Kanzo Board for Hermes Desktop: your Kanzo board as a sidebar page.
//
// When a board answers, the page shows the board's own web UI. The backend
// (dashboard/plugin_api.py + frame.py) fetches it from the running Kanzo and returns
// one document with a small bridge (dashboard/bridge.js) in front of app.js; this
// page shows it in the SDK's SandboxedFrame and answers the bridge's messages.
// When no board answers, the page offers setup instead: install Kanzo, start it,
// or join a board another computer shares.
import { useQuery, useQueryClient, useMutation, SandboxedFrame, ErrorState, Skeleton, Button, Input,
  ROUTES_AREA, SIDEBAR_NAV_AREA, PALETTE_AREA, host, pluginSettingsHref } from '@hermes/plugin-sdk';
import { useEffect, useMemo, useRef, useState } from 'react';
import { jsx, jsxs } from 'react/jsx-runtime';

const ID = 'kanzo-board';
const PATH = '/kanzo-board';
const STORAGE_KEY = 'localStorage';
const KANZO_URL = 'https://github.com/emanuele-em/kanzo';

const muted = { color: 'var(--ui-text-tertiary)' };
const faint = { color: 'var(--ui-text-quaternary)' };

function toDataUrl(html) {
  const bytes = new TextEncoder().encode(html);
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return 'data:text/html;charset=utf-8;base64,' + btoa(s);
}

const errorText = e => String((e && e.message) || e || 'Something went wrong').replace(/^\d{3}:\s*/, '')
  .replace(/^\{"detail":"(.*)"\}$/, '$1');

// --- setup ------------------------------------------------------------------------------------

function Section({ title, children }) {
  return jsxs('section', { className: 'space-y-2 rounded-xl p-4', style: { border: '1px solid var(--ui-stroke-secondary)' },
    children: [jsx('h2', { className: 'text-sm font-semibold', children: title }), children] });
}

const Note = ({ children }) => jsx('p', { className: 'text-xs leading-relaxed', style: faint, children });
const Code = ({ children }) => jsx('code', { className: 'text-[0.75rem]', children });

function Setup({ ctx, status, refresh }) {
  const qc = useQueryClient();
  const [host_, setHost] = useState('');
  const run = useMutation({
    mutationFn: ({ path, body }) => ctx.rest(path, { method: 'POST', body: body || {}, timeoutMs: 180000 }),
    onSuccess: data => { qc.setQueryData([ID, 'status'], data); qc.invalidateQueries({ queryKey: [ID, 'shell'] }); },
  });
  const busy = run.isPending;
  const step = (path, body) => run.mutate({ path, body });
  const { board, kanzo, release } = status;
  const remote = board.source === 'setting';
  const openSettings = () => host.navigate(pluginSettingsHref ? pluginSettingsHref(ID) : '/settings?tab=plugins');

  let local;
  if (remote) {
    local = jsxs(Section, { title: 'Board from the plugin settings', children: [
      jsxs('p', { className: 'text-sm', style: muted, children: ['No Kanzo board answers at ', jsx(Code, { children: board.url }), '.'] }),
      jsx(Note, { children: 'Check that the board is running and reachable from the computer that runs Hermes, or clear the board URL in the plugin settings to use a board on this computer.' }),
      jsxs('div', { className: 'flex gap-2', children: [
        jsx(Button, { size: 'sm', disabled: busy, onClick: refresh, children: 'Try again' }),
        jsx(Button, { size: 'sm', variant: 'outline', onClick: openSettings, children: 'Plugin settings' }),
      ] }),
    ] });
  } else if (!kanzo) {
    local = jsxs(Section, { title: 'Kanzo on this computer', children: [
      jsx('p', { className: 'text-sm', style: muted, children: 'Kanzo is not installed yet.' }),
      release.supported
        ? jsxs('div', { className: 'space-y-2', children: [
          jsx(Button, { size: 'sm', disabled: busy, onClick: () => step('/setup/install'),
            children: busy ? 'Installing…' : `Install Kanzo ${release.version}` }),
          jsxs(Note, { children: ['Downloads the official release from ', jsx(Code, { children: 'github.com/emanuele-em/kanzo' }),
            ', checks it against a SHA-256 pinned in this plugin, and installs the ', jsx(Code, { children: 'kanzo' }),
            ' program to ', jsx(Code, { children: release.install_dir }), ', where Kanzo\'s own installer puts it.'] }),
        ] })
        : jsxs(Note, { children: ['Kanzo publishes no build for this computer. Install it from ',
          jsx(Code, { children: KANZO_URL }), ', then try again.'] }),
    ] });
  } else {
    local = jsxs(Section, { title: 'Kanzo on this computer', children: [
      jsxs('p', { className: 'text-sm', style: muted, children: [`Kanzo ${kanzo.version || ''} is installed at `,
        jsx(Code, { children: kanzo.path }), ', but its board is not running.'] }),
      jsxs('div', { className: 'flex flex-wrap gap-2', children: [
        jsx(Button, { size: 'sm', disabled: busy, onClick: () => step('/setup/start', { mode: 'service' }),
          children: busy ? 'Starting…' : 'Start, and keep it running' }),
        jsx(Button, { size: 'sm', variant: 'outline', disabled: busy, onClick: () => step('/setup/start', { mode: 'now' }),
          children: 'Start once' }),
      ] }),
      jsxs(Note, { children: ['Start, and keep it running uses ', jsx(Code, { children: 'kanzo service install' }),
        ': the board starts at login (a LaunchAgent on macOS, a systemd user service on Linux, Task Scheduler on Windows). ',
        'Undo it any time with ', jsx(Code, { children: 'kanzo service uninstall' }), '. Start once runs it until you log out.'] }),
    ] });
  }

  return jsx('div', { className: 'h-full overflow-y-auto', children: jsxs('div', { className: 'mx-auto max-w-xl space-y-4 p-8', children: [
    jsxs('div', { className: 'space-y-1', children: [
      jsx('h1', { className: 'text-lg font-semibold', children: 'Connect a Kanzo board' }),
      jsxs('p', { className: 'text-sm', style: muted, children: [
        'This page shows your ', jsx('a', { href: KANZO_URL, className: 'underline', onClick: e => { e.preventDefault(); ctx.os.openExternal(KANZO_URL); }, children: 'Kanzo' }),
        ' board, the self-hosted kanban for people and agents, inside Hermes.'] }),
    ] }),
    local,
    !remote && jsxs(Section, { title: 'A board another computer shares', children: [
      jsxs('form', { className: 'flex gap-2', onSubmit: e => { e.preventDefault(); if (host_.trim()) step('/setup/join', { host: host_ }); }, children: [
        jsx(Input, { value: host_, onChange: e => setHost(e.target.value), placeholder: '192.168.1.20', disabled: busy || !kanzo, className: 'h-8 max-w-56' }),
        jsx(Button, { size: 'sm', type: 'submit', variant: 'outline', disabled: busy || !kanzo || !host_.trim(), children: 'Join' }),
      ] }),
      jsxs(Note, { children: ['On the computer with the board, open Kanzo, click the share icon and turn on ',
        jsx('b', { children: 'Share this board' }), '; enter the address it shows. Kanzo on this computer then shows the shared board, ',
        'and your agents use it too. Install and start Kanzo here first.'] }),
    ] }),
    !remote && jsxs(Note, { children: ['Board on a server, or Hermes running somewhere else? Set its address under ',
      jsx('a', { href: '#', className: 'underline', onClick: e => { e.preventDefault(); openSettings(); }, children: 'Settings → Plugins → Kanzo Board' }), '.'] }),
    run.isError && jsx('p', { role: 'alert', className: 'text-sm text-destructive', children: errorText(run.error) }),
  ] }) });
}

// --- "let the agent use the board" -----------------------------------------------------------

function AgentToolsBar({ ctx, status }) {
  const qc = useQueryClient();
  const [hidden, setHidden] = useState(() => ctx.storage.get('hideAgentTools', false));
  const add = useMutation({
    mutationFn: () => ctx.rest('/setup/mcp', { method: 'POST', body: {}, timeoutMs: 120000 }),
    onSuccess: data => {
      qc.setQueryData([ID, 'status'], data);
      host.notify({ kind: 'success', message: 'Kanzo\'s tools are added. Start a new chat, or run /reload-mcp, to use them.' });
    },
    onError: e => host.notify({ kind: 'error', message: errorText(e) }),
  });
  if (hidden || (status.mcp && status.mcp.server)) return null;
  return jsxs('div', { className: 'flex items-center gap-3 px-4 py-2 text-sm',
    style: { borderBottom: '1px solid var(--ui-stroke-secondary)' }, children: [
      jsx('span', { className: 'min-w-0 flex-1', style: muted, children: 'Let your Hermes agent read and update this board with Kanzo\'s MCP tools.' }),
      jsx(Button, { size: 'sm', disabled: add.isPending, onClick: () => add.mutate(), children: add.isPending ? 'Adding…' : 'Add Kanzo tools' }),
      jsx(Button, { size: 'sm', variant: 'ghost', onClick: () => { ctx.storage.set('hideAgentTools', true); setHidden(true); }, children: 'Not now' }),
    ] });
}

// --- the board ------------------------------------------------------------------------------

function Board({ ctx, status }) {
  const qc = useQueryClient();
  const frame = useRef(null);
  const shell = useQuery({
    queryKey: [ID, 'shell', status.board.url],
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
            try {
              return reply(await ctx.rest('/proxy', { method: 'POST', body: d.req, timeoutMs: 60000 }));
            } catch (err) {
              // The board went away: check now, so the page offers setup instead of a dead board.
              qc.invalidateQueries({ queryKey: [ID, 'status'] });
              throw err;
            }
          case 'storage':
            return ctx.storage.set(STORAGE_KEY, d.data || {});
          case 'copy':
            return reply(await ctx.os.writeClipboard(String(d.text)));
          case 'open':
            if (typeof d.url === 'string' && /^https?:\/\//i.test(d.url)) await ctx.os.openExternal(d.url);
            return;
          case 'version':
            // Kanzo was updated under a loaded page: load its new UI.
            if (shell.data && shell.data.version && d.version && d.version !== shell.data.version) {
              qc.invalidateQueries({ queryKey: [ID, 'shell'] });
            }
            return;
        }
      } catch (err) {
        if (d.id) reply(undefined, errorText(err));
      }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [shell.data]);

  if (shell.isPending) return jsx('div', { className: 'p-6', children: jsx(Skeleton, { className: 'h-64 w-full' }) });
  if (shell.isError || !src) {
    return jsx(ErrorState, {
      title: 'Could not load the board',
      description: errorText(shell.error) || 'The board sent no page.',
      children: jsx(Button, { variant: 'outline', onClick: () => qc.invalidateQueries({ queryKey: [ID] }), children: 'Try again' }),
    });
  }
  return jsx(SandboxedFrame, {
    ref: frame, src, title: 'Kanzo board', sandbox: 'allow-scripts allow-forms allow-downloads',
    style: { width: '100%', height: '100%', border: 0, display: 'block' },
  });
}

function KanzoPage({ ctx }) {
  const qc = useQueryClient();
  const status = useQuery({
    queryKey: [ID, 'status'],
    queryFn: () => ctx.rest('/status', { timeoutMs: 20000 }),
    refetchInterval: q => (q.state.data && q.state.data.board && q.state.data.board.reachable ? 30000 : 5000),
  });
  useEffect(() => ctx.onEvent(`plugin.${ID}.settings.changed`, () => qc.invalidateQueries({ queryKey: [ID] })), []);

  if (status.isPending) return jsx('div', { className: 'p-6', children: jsx(Skeleton, { className: 'h-64 w-full' }) });
  if (status.isError) {
    return jsx(ErrorState, {
      title: 'Kanzo Board is not ready',
      description: `${errorText(status.error)}. If you just installed or updated the plugin, restart the Hermes gateway (hermes gateway restart).`,
      children: jsx(Button, { variant: 'outline', onClick: () => status.refetch(), children: 'Try again' }),
    });
  }
  const s = status.data;
  if (!s.board.reachable) return jsx(Setup, { ctx, status: s, refresh: () => status.refetch() });
  return jsxs('div', { className: 'flex h-full flex-col', children: [
    jsx(AgentToolsBar, { ctx, status: s }),
    jsx('div', { className: 'relative min-h-0 flex-1', children: jsx(Board, { ctx, status: s }) }),
  ] });
}

export default {
  id: ID, name: 'Kanzo Board',
  register(ctx) {
    ctx.registerMany([
      { id: 'page', area: ROUTES_AREA, data: { path: PATH },
        render: () => jsx('div', { style: { height: '100%', width: '100%' }, children: jsx(KanzoPage, { ctx }) }) },
      { id: 'nav', area: SIDEBAR_NAV_AREA, data: { path: PATH, label: 'Kanzo', codicon: 'project' } },
      { id: 'cmd', area: PALETTE_AREA, data: { label: 'Open Kanzo board', run: () => host.navigate(PATH) } },
    ]);
  },
};
