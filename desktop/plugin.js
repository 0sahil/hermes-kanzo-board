// Kanzo board for Hermes Desktop: sidebar page that mirrors the Kanzo web UI.
import { useQuery, useQueryClient, Dialog, DialogContent, DialogHeader, DialogTitle, EmptyState, ErrorState,
  Skeleton, ROUTES_AREA, SIDEBAR_NAV_AREA, PALETTE_AREA, host } from '@hermes/plugin-sdk';
import { useState, useMemo } from 'react';
import { jsx, jsxs } from 'react/jsx-runtime';

const ID = 'kanzo';
const PROJECT_COLORS = { red: '#ef4444', orange: '#f97316', yellow: '#eab308', green: '#22c55e',
  teal: '#14b8a6', blue: '#3b82f6', purple: '#a855f7', pink: '#ec4899', gray: '#8e8e93' };
const STATUS_COLORS = ['#8a8a83', '#3b82f6', '#e8a317', '#2f9e44', '#ae3ec9', '#e8590c'];

function projectColor(p) {
  if (p && PROJECT_COLORS[p.color]) return PROJECT_COLORS[p.color];
  const names = Object.keys(PROJECT_COLORS).filter(n => n !== 'gray');
  let h = 0;
  for (const c of (p ? p.slug : '')) h = (h * 31 + c.charCodeAt(0)) % 997;
  return PROJECT_COLORS[names[h % names.length]];
}

function StatusIcon({ status, statuses }) {
  const todo = statuses.indexOf('todo');
  const step = statuses.indexOf(status) - todo;
  const steps = statuses.indexOf('done') - todo;
  const f = Math.max(step, 0) / steps;
  const color = STATUS_COLORS[Math.max(step, 0) % STATUS_COLORS.length];
  const kids = [jsx('circle', { key: 'c', cx: 7, cy: 7, r: 6, fill: 'none', stroke: color, strokeWidth: 1.5 })];
  if (f >= 1) {
    kids.push(jsx('circle', { key: 'f', cx: 7, cy: 7, r: 6, fill: color }));
    kids.push(jsx('path', { key: 'k', d: 'm4.4 7.2 1.8 1.8 3.4-3.6', fill: 'none', stroke: 'var(--background)',
      strokeWidth: 1.6, strokeLinecap: 'round', strokeLinejoin: 'round' }));
  } else if (f > 0) {
    const r = 3.4, a = f * 2 * Math.PI;
    kids.push(jsx('path', { key: 'p', fill: color,
      d: `M7 7L7 ${7 - r}A${r} ${r} 0 ${f > 0.5 ? 1 : 0} 1 ${(7 + r * Math.sin(a)).toFixed(2)} ${(7 - r * Math.cos(a)).toFixed(2)}Z` }));
  }
  return jsx('svg', { viewBox: '0 0 14 14', width: 14, height: 14, className: 'shrink-0', children: kids });
}

const flat = 'color-mix(in srgb, var(--foreground) 5%, var(--background))';
const raised = 'color-mix(in srgb, var(--foreground) 8%, var(--background))';
const hover = 'color-mix(in srgb, var(--foreground) 12%, var(--background))';
const faint = { color: 'var(--ui-text-quaternary)' };
const muted = { color: 'var(--ui-text-tertiary)' };

function Tag({ name }) {
  return jsx('span', { className: 'rounded-full px-2 text-xs', style: { background: hover, ...muted }, children: name });
}

function Card({ t, project, statuses, onOpen, onDragStart }) {
  return jsxs('div', {
    draggable: true,
    onDragStart: e => { e.dataTransfer.setData('text/plain', String(t.id)); onDragStart(t.id); },
    onClick: () => onOpen(t.id),
    className: 'cursor-grab rounded-[14px] px-3 py-2.5 text-sm',
    style: { background: raised, border: '1px solid var(--ui-stroke-secondary)' },
    onMouseEnter: e => { e.currentTarget.style.background = hover; },
    onMouseLeave: e => { e.currentTarget.style.background = raised; },
    children: [
      jsxs('div', { className: 'flex items-start gap-2.5', children: [
        jsx('div', { className: 'min-w-0 flex-1 break-words', children: t.title }),
        t.human ? jsx('span', { title: 'Needs a human', style: muted, children: '👤' }) : null,
        jsxs('span', { className: 'mt-0.5 inline-flex shrink-0 items-center gap-1 text-xs tabular-nums', style: faint, children: [
          jsx('span', { className: 'inline-block h-1.5 w-1.5 rounded-full', style: { background: projectColor(project) } }),
          `#${t.id}`] }),
      ] }),
      t.description ? jsx('span', { className: 'mt-0.5 block truncate text-[13px]', style: muted, children: t.description.replace(/\s+/g, ' ') }) : null,
      (t.tags && t.tags.length) ? jsx('div', { className: 'mt-1.5 flex flex-wrap gap-1',
        children: t.tags.map(n => jsx(Tag, { key: String(n.name || n), name: String(n.name || n) })) }) : null,
    ],
  });
}

function Column({ status, tasks, projects, statuses, collapsed, toggle, onOpen, onDrop, setDrag }) {
  const [over, setOver] = useState(false);
  if (collapsed) return jsxs('section', {
    onClick: toggle,
    onDragOver: e => e.preventDefault(), onDrop: e => { e.preventDefault(); onDrop(status, null); },
    className: 'flex w-12 shrink-0 cursor-pointer flex-col items-center gap-2.5 rounded-[18px] py-3',
    style: { background: flat },
    children: [
      jsx(StatusIcon, { status, statuses }),
      jsxs('span', { className: 'text-[13px] font-semibold capitalize', style: { writingMode: 'vertical-rl', ...muted },
        children: [status, ' ', jsx('span', { style: faint, className: 'font-normal', children: tasks.length })] }),
    ] });
  return jsxs('section', {
    className: 'flex min-h-0 w-[336px] shrink-0 flex-col rounded-[18px]',
    style: { background: over ? hover : flat },
    onDragOver: e => { e.preventDefault(); setOver(true); },
    onDragLeave: () => setOver(false),
    onDrop: e => { e.preventDefault(); setOver(false); onDrop(status, null); },
    children: [
      jsxs('h2', { className: 'flex items-center gap-2 px-4 pb-2.5 pt-3.5 text-[13px] font-semibold capitalize', style: muted, children: [
        jsx(StatusIcon, { status, statuses }), status,
        jsx('span', { className: 'font-normal', style: faint, children: tasks.length }),
        status === 'done' ? jsx('button', { onClick: toggle, className: 'ml-auto', style: faint, title: 'Collapse', children: '«' }) : null,
      ] }),
      jsx('div', { className: 'flex min-h-2 flex-col gap-1.5 overflow-y-auto px-2 pb-2',
        children: tasks.map(t => jsx('div', { key: t.id,
          onDragOver: e => e.preventDefault(),
          onDrop: e => { e.preventDefault(); e.stopPropagation(); setOver(false); onDrop(status, t.id); },
          children: jsx(Card, { t, project: projects[t.project], statuses, onOpen, onDragStart: setDrag }) })) }),
    ],
  });
}

function TaskDialog({ id, ctx, onClose, projects }) {
  const q = useQuery({ queryKey: [ID, 'task', id], enabled: id != null, queryFn: () => ctx.rest(`/task/${id}`) });
  const t = q.data && q.data.task;
  const comments = (q.data && q.data.comments) || [];
  return jsx(Dialog, { open: id != null, onOpenChange: o => { if (!o) onClose(); }, children:
    jsxs(DialogContent, { className: 'max-h-[80vh] overflow-y-auto', children: [
      jsx(DialogHeader, { children: jsx(DialogTitle, { children: t ? t.title : 'Loading…' }) }),
      !t ? jsx(Skeleton, { className: 'h-24 w-full' }) : jsxs('div', { className: 'space-y-3 text-sm', children: [
        jsxs('div', { className: 'flex flex-wrap items-center gap-2 text-xs', style: muted, children: [
          jsx('span', { children: `${t.project || ''}#${t.id}` }), jsx('span', { children: t.status }),
          ...(t.tags || []).map(n => jsx(Tag, { key: String(n.name || n), name: String(n.name || n) })),
          t.url ? jsx('a', { href: t.url, onClick: e => { e.preventDefault(); ctx.os.openExternal(t.url); }, className: 'underline', children: 'link' }) : null ] }),
        jsx('div', { className: 'whitespace-pre-wrap break-words', children: t.description || 'No description.' }),
        ...(comments.map(c => jsxs('div', { key: c.id, className: 'rounded-lg p-2', style: { background: flat }, children: [
          jsx('div', { className: 'text-xs', style: faint, children: c.created_at }),
          jsx('div', { className: 'whitespace-pre-wrap break-words', children: c.body }) ] }))),
      ] }),
    ] }) });
}

function Page({ ctx }) {
  const qc = useQueryClient();
  const [project, setProject] = useState('');
  const [filter, setFilter] = useState('');
  const [collapsed, setCollapsed] = useState({ done: true });
  const [open, setOpen] = useState(null);
  const [drag, setDrag] = useState(null);
  const key = [ID, 'board', project, filter];
  const q = useQuery({ queryKey: key, refetchInterval: 10000,
    queryFn: () => ctx.rest(`/board?project=${encodeURIComponent(project)}&q=${encodeURIComponent(filter)}`) });
  const projects = useMemo(() => Object.fromEntries((q.data?.projects || []).map(p => [p.slug, p])), [q.data]);

  if (q.isPending) return jsx('div', { className: 'p-6', children: jsx(Skeleton, { className: 'h-64 w-full' }) });
  if (q.isError) return jsx(ErrorState, { title: 'Kanzo board unreachable',
    description: String(q.error?.message || q.error) + ' — is the board running (kanzo)?' });

  const { statuses, tasks } = q.data;
  const all = q.data.projects;
  const total = all.reduce((n, p) => n + p.open, 0);
  const drop = async (status, before) => {
    if (drag == null) return;
    const id = drag; setDrag(null);
    try { await ctx.rest('/move', { method: 'POST', body: { id, status, before } }); }
    catch (e) { host.notify({ kind: 'error', message: String(e.message || e) }); }
    qc.invalidateQueries({ queryKey: [ID, 'board'] });
  };
  const navItem = (slug, label, count, color) => jsxs('button', {
    key: slug, onClick: () => setProject(slug),
    className: 'flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-sm',
    style: { background: project === slug ? raised : 'transparent' },
    children: [
      color ? jsx('span', { className: 'inline-block h-2.5 w-2.5 shrink-0 rounded-sm', style: { background: color } }) : null,
      jsx('span', { className: 'min-w-0 flex-1 truncate', children: label }),
      jsx('span', { className: 'text-xs tabular-nums', style: faint, children: count }) ] });

  return jsxs('div', { className: 'flex h-full min-h-0', children: [
    jsxs('aside', { className: 'flex w-56 shrink-0 flex-col gap-0.5 overflow-y-auto p-3', style: { borderRight: '1px solid var(--ui-stroke-secondary)' }, children: [
      navItem('', 'All projects', total, null),
      jsx('div', { className: 'px-2.5 pb-1 pt-3 text-xs', style: faint, children: 'Projects' }),
      ...all.map(p => navItem(p.slug, p.name, p.open, projectColor(p))),
      jsx('button', { className: 'mt-auto px-2.5 py-1.5 text-left text-xs underline', style: muted,
        onClick: () => ctx.os.openExternal(q.data.url || 'http://127.0.0.1:4242'), children: 'Open Kanzo in browser' }),
    ] }),
    jsxs('div', { className: 'flex min-w-0 flex-1 flex-col', children: [
      jsxs('div', { className: 'flex items-center gap-3 px-6 py-4', children: [
        jsx('h1', { className: 'text-lg font-semibold', children: project ? (projects[project]?.name || project) : 'All projects' }),
        jsx('span', { className: 'text-sm', style: muted, children: project ? `${projects[project]?.open ?? 0} open tasks` : `${total} open tasks in ${all.length} projects` }),
        jsx('input', { value: filter, onChange: e => setFilter(e.target.value), placeholder: 'Filter board',
          className: 'ml-auto w-56 rounded-full px-3.5 py-1.5 text-sm outline-none',
          style: { background: flat, border: '1px solid var(--ui-stroke-secondary)', color: 'var(--foreground)' } }),
      ] }),
      tasks.length === 0 && !statuses.length ? jsx(EmptyState, { title: 'No tasks' }) :
      jsx('div', { className: 'flex min-h-0 flex-1 gap-3 overflow-x-auto px-6 pb-6',
        children: statuses.map(s => jsx(Column, { key: s, status: s, statuses, projects,
          tasks: tasks.filter(t => t.status === s), collapsed: !!collapsed[s],
          toggle: () => setCollapsed(c => ({ ...c, [s]: !c[s] })),
          onOpen: setOpen, onDrop: drop, setDrag })) }),
    ] }),
    jsx(TaskDialog, { id: open, ctx, onClose: () => setOpen(null), projects }),
  ] });
}

export default {
  id: ID, name: 'Kanzo', defaultEnabled: true,
  register(ctx) {
    ctx.registerMany([
      { id: 'page', area: ROUTES_AREA, data: { path: '/kanzo' }, render: () => jsx(Page, { ctx }) },
      { id: 'nav', area: SIDEBAR_NAV_AREA, data: { path: '/kanzo', label: 'Kanzo', codicon: 'project' } },
      { id: 'cmd', area: PALETTE_AREA, data: { label: 'Open Kanzo board', run: () => host.navigate('/kanzo') } },
    ]);
  },
};
