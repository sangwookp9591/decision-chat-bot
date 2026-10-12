import { Suspense, useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { Route, Routes, useLocation } from 'react-router-dom';
import { useSession, type SessionUser } from '../state/session';
import { APP_NAME } from '../lib/brand';
import { apiFetch } from '../api/client';
import { reviewApi } from '../api/reviews';
import { roleLabel } from '../components/statusLabels';
import { Main } from '../pages/Main';
import { Skeleton } from '../pages/main/ProgressivePanel';
import { Cases, Evaluation, JudgmentMap, Learning, Monitoring, Observatory, Policy, PrefetchNavLink, Review, Tasks, usePrefetchWhenIdle } from './routes';

/** 24px line icons, stroke follows the link colour. */
const icon = (d: ReactNode) => <svg className="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{d}</svg>;
const icons = {
  chat: icon(<path d="M4 5h16v11H9l-5 4z" />),
  review: icon(<><path d="M12 3 4 6v6c0 4.5 3.4 8 8 9 4.6-1 8-4.5 8-9V6z" /><path d="m9 12 2 2 4-4" /></>),
  tasks: icon(<><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M9 8v8M15 8v5" /></>),
  observatory: icon(<><circle cx="6" cy="6" r="2" /><circle cx="18" cy="6" r="2" /><circle cx="12" cy="18" r="2" /><path d="M7.5 7.5 11 16.5M16.5 7.5 13 16.5M8 6h8" /></>),
  map: icon(<path d="m12 3 9 5-9 5-9-5zM3 13l9 5 9-5" />),
  monitoring: icon(<path d="M3 12h4l3-7 4 14 3-7h4" />),
  cases: icon(<><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M8 8h8M8 12h8M8 16h5" /></>),
  learning: icon(<><path d="M20 12a8 8 0 1 1-2.3-5.7" /><path d="M20 4v4h-4" /></>),
  evaluation: icon(<><rect x="4" y="3" width="16" height="18" rx="2" /><path d="m8 12 3 3 5-6" /></>),
  policy: icon(<path d="M5 4v16M12 4v16M19 4v16M3 8h4M10 15h4M17 10h4" />),
};

type NavItem = { to: string; label: string; icon: ReactNode };
/** Menu grouped by what the person is doing: handle work, watch the system, improve the rules. */
export const navGroups: { label: string; items: NavItem[] }[] = [
  { label: '업무', items: [{ to: '/', label: '요청 접수', icon: icons.chat }, { to: '/review', label: '검토 대기', icon: icons.review }, { to: '/tasks', label: '업무', icon: icons.tasks }] },
  { label: '관찰', items: [{ to: '/observatory', label: '실행 관찰', icon: icons.observatory }, { to: '/judgment-map', label: '판단 맵', icon: icons.map }, { to: '/monitoring', label: '모니터링', icon: icons.monitoring }] },
  { label: '개선', items: [{ to: '/cases', label: '판단 사례', icon: icons.cases }, { to: '/learning', label: '규칙 학습', icon: icons.learning }, { to: '/evaluation', label: '평가 라벨', icon: icons.evaluation }, { to: '/policy', label: '정책', icon: icons.policy }] },
];
const allItems = navGroups.flatMap((group) => group.items);
const modeLabel = { live: '실서비스 연결', mock: 'mock 응답' } as const;
const COUNT_CAP = 99;

async function logout() {
  try { await apiFetch('/api/auth/logout', { method: 'POST' }); } catch { /* the local session is cleared below even if the endpoint is missing */ }
  window.dispatchEvent(new CustomEvent('auth:unauthorized'));
}

/** Pending reviews visible to this reviewer; refreshed on navigation. Non-reviewers never call the queue. */
function usePendingReviews(isReviewer: boolean) {
  const { pathname } = useLocation();
  const [count, setCount] = useState<number | null>(null);
  useEffect(() => {
    if (!isReviewer) return;
    let live = true;
    reviewApi.list('pending').then((data) => { if (live) setCount(data.reviews.length); }, () => { if (live) setCount(null); });
    return () => { live = false; };
  }, [isReviewer, pathname]);
  return isReviewer ? count : null;
}

function AccountMenu({ user }: { user: SessionUser | null }) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const name = user?.name || user?.id || '';
  const roles = (user?.roles || []).map(roleLabel);
  useEffect(() => {
    if (!open) return;
    const outside = (event: MouseEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', outside);
    return () => document.removeEventListener('mousedown', outside);
  }, [open]);
  const close = () => { setOpen(false); trigger.current?.focus(); };
  return <div className="account" ref={root}>
    <button ref={trigger} type="button" className="account-trigger" aria-haspopup="menu" aria-expanded={open} aria-controls={open ? menuId : undefined} onClick={() => setOpen((value) => !value)}>
      <span className="account-avatar" aria-hidden="true">{name.slice(0, 1)}</span>
      <span className="account-name">{name}</span>
      {roles.length > 0 && <span className="account-role">{roles[0]}{roles.length > 1 ? ` +${roles.length - 1}` : ''}</span>}
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
    </button>
    {open && <div id={menuId} role="menu" aria-label="계정" className="account-menu" onKeyDown={(event) => { if (event.key === 'Escape') close(); }}>
      <div className="account-menu-head"><strong>{name}</strong>{roles.length > 0 && <span>{roles.join(' · ')}</span>}</div>
      <button type="button" role="menuitem" className="account-menu-item" onClick={() => { setOpen(false); void logout(); }}>로그아웃</button>
    </div>}
  </div>;
}

function Sidebar({ pending }: { pending: number | null }) {
  return <aside className="app-sidebar">
    <div className="brand">{APP_NAME}</div>
    <nav aria-label="주 메뉴">{navGroups.map((group) => <div key={group.label} role="group" aria-label={group.label} className="nav-group">
      <span className="nav-caption" aria-hidden="true">{group.label}</span>
      {group.items.map((item) => {
        const count = item.to === '/review' && pending ? pending : 0;
        const shown = count > COUNT_CAP ? `${COUNT_CAP}+` : String(count);
        const name = count ? `${item.label} ${count > COUNT_CAP ? `${COUNT_CAP}건 이상` : `${count}건`}` : undefined;
        return <PrefetchNavLink key={item.to} to={item.to} end={item.to === '/'} aria-label={name}>{item.icon}<span>{item.label}</span>{count > 0 && <span className="nav-count" aria-hidden="true">{shown}</span>}</PrefetchNavLink>;
      })}
    </div>)}</nav>
  </aside>;
}

const placeholder = (label: string) => <section><h1>{label}</h1><div className="empty"><div className="mark" aria-hidden="true">◇</div><h2>화면 준비 중</h2><p>이 화면은 기능 연결 단계에서 제공됩니다.</p></div></section>;

export function AppShell() {
  const { user } = useSession();
  const roles = user?.roles || [];
  const pending = usePendingReviews(roles.includes('reviewer'));
  usePrefetchWhenIdle(allItems.map((item) => item.to).filter((to) => to !== '/'));
  const pages: Record<string, ReactNode> = {
    '/': <Main />, '/review': <Review />, '/tasks': <Tasks />, '/observatory': <Observatory />, '/judgment-map': <JudgmentMap />, '/monitoring': <Monitoring />,
    '/cases': <Cases />, '/learning': <Learning roles={roles} />, '/evaluation': <Evaluation />, '/policy': <Policy canEdit={roles.includes('policy_editor')} />,
  };
  return <div className="layout">
    <Sidebar pending={pending} />
    <div className="app-main">
      <header className="topbar">
        <span>의사결정 지원</span>
        <div className="topbar-account">
          {user?.mode && <span className={`environment-badge mode-${user.mode}`}><i aria-hidden="true" />{modeLabel[user.mode]}</span>}
          <AccountMenu user={user} />
        </div>
      </header>
      <main><Suspense fallback={<Skeleton rows={4} label="화면을 불러오는 중" />}><Routes>
        {allItems.map((item) => <Route key={item.to} path={item.to} element={pages[item.to] ?? placeholder(item.label)} />)}
        <Route path="*" element={<section><h1>페이지를 찾을 수 없습니다</h1></section>} />
      </Routes></Suspense></main>
    </div>
  </div>;
}
