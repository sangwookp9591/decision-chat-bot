import { useCallback, useEffect, useRef, useState } from 'react';
import { requestApi, type RequestDetail, type RequestItem } from '../../api/requests';
import { getStatusPresentation } from '../../components/statusLabels';
import { groupLabel, shortId, titleFromDetail } from './listFormat';
import { PlusIcon } from './icons';

/** The list API has no title yet; if the server ever adds one (`title`/`preview`), it wins over the per-row detail fetch. */
type ListItem = RequestItem & { title?: string; preview?: string };
const CONCURRENCY = 3; const FALLBACK_EAGER = 12;

/**
 * Row titles come from each request's first revision, fetched only for rows that scroll into view (3 at a time) and cached for the
 * life of the page. `known` seeds titles that are already loaded (the open conversation) so they cost no request.
 */
export function useRequestTitles(known: RequestDetail | null) {
  const [titles, setTitles] = useState<Record<string, string>>({});
  const asked = useRef(new Set<string>()); const queue = useRef<string[]>([]); const running = useRef(0); const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []); // set again on mount: StrictMode runs the cleanup once in dev
  const pump = useCallback(() => {
    while (running.current < CONCURRENCY && queue.current.length) {
      const id = queue.current.shift()!; running.current += 1;
      Promise.resolve().then(() => requestApi.detail(id))
        .then((detail) => titleFromDetail(detail), () => '')
        .then((title) => { if (alive.current) setTitles((current) => ({ ...current, [id]: title || '제목 없는 요청' })); })
        .finally(() => { running.current -= 1; pump(); });
    }
  }, []);
  const want = useCallback((id: string) => { if (asked.current.has(id)) return; asked.current.add(id); queue.current.push(id); pump(); }, [pump]);
  useEffect(() => {
    if (!known) return;
    const title = titleFromDetail(known);
    if (title) { asked.current.add(known.request.id); setTitles((current) => (current[known.request.id] === title ? current : { ...current, [known.request.id]: title })); }
  }, [known]);
  return { titles, want };
}

function Row({ item, title, current, onOpen, onVisible }: { item: ListItem; title?: string; current: boolean; onOpen: () => void; onVisible: () => void }) {
  const ref = useRef<HTMLButtonElement>(null);
  const state = getStatusPresentation(item.status);
  const shown = item.title || item.preview || title;
  useEffect(() => {
    if (shown) return;
    const node = ref.current;
    if (!node || typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver((entries) => { if (entries.some((entry) => entry.isIntersecting)) { onVisible(); observer.disconnect(); } }, { rootMargin: '120px' });
    observer.observe(node); return () => observer.disconnect();
  }, [shown, onVisible]);
  const long = item.id.length > 8; // the full id stays reachable for assistive tech and text search; the short one is the visible aid
  return <button ref={ref} type="button" className="request-row" onClick={onOpen} aria-current={current ? 'true' : undefined}>
    <span className="status-dot" data-status={state.status} role="img" aria-label={state.label} title={state.label} />
    {shown ? <span className="request-title">{shown}</span> : <span className="request-title ui-skeleton" aria-label="제목을 불러오는 중" />}
    <code className="request-id" title={item.id} aria-hidden={long || undefined}>{shortId(item.id)}</code>{long && <span className="sr-only">{item.id}</span>}
  </button>;
}

/** "내 요청 대화": a chat-style sidebar. New-request button on top, day groups, one line per request; it scrolls on its own inside the screen height. */
export function RequestList({ items, currentId, titles, want, onOpen, onNew, hideTitle }: { items: ListItem[]; currentId: string; titles: Record<string, string>; want: (id: string) => void; onOpen: (id: string) => void; onNew: () => void; hideTitle?: boolean }) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => { const timer = window.setInterval(() => setNow(new Date()), 60_000); return () => window.clearInterval(timer); }, []);
  useEffect(() => { if (typeof IntersectionObserver === 'undefined') items.slice(0, FALLBACK_EAGER).forEach((item) => want(item.id)); }, [items, want]);
  const groups: Array<{ label: string; items: ListItem[] }> = [];
  items.forEach((item) => { const label = groupLabel(item.created_at, now); const last = groups[groups.length - 1]; if (last?.label === label) last.items.push(item); else groups.push({ label, items: [item] }); });
  return <div className="list-body"><div className="list-head"><button type="button" className="new-chat" onClick={onNew}><PlusIcon />새 요청</button>{!hideTitle && <h2>내 요청 대화</h2>}</div>
    <div className="list-scroll">{groups.length ? groups.map((group) => <section key={group.label} className="list-group" aria-label={group.label}><h3>{group.label}</h3>{group.items.map((item) => <Row key={item.id} item={item} title={titles[item.id]} current={item.id === currentId} onOpen={() => onOpen(item.id)} onVisible={() => want(item.id)} />)}</section>) : <p className="list-empty">접수한 요청이 여기에 표시됩니다.</p>}</div>
  </div>;
}
