import { useEffect, useMemo, useState } from 'react';
import type { ApiError } from '../api/client';
import { userApi, type AdminOrg, type AdminUser, type UserHistory, type UserState } from '../api/users';
import { Button, Modal, StatusBadge, Toast } from '../components';
import { ShortId } from '../components/ShortId';
import { ChipGroup, EmptyCard, Switch, TextField } from '../components/fields';
import { roleLabel } from '../components/statusLabels';
import { formatTime } from '../lib/format';
import './review/review.css';
import './cases/cases.css';
import './admin/admin.css';

/** What each role opens — shown next to its toggle so an admin grants a permission knowing what it does. */
export const roleHelp: Record<string, string> = {
  requester: '요청 접수에서 업무를 요청하고 내 요청 결과를 봅니다.',
  reviewer: '소속 조직에 배정된 검토를 승인·반려하고 판단 사례를 다룹니다.',
  team_member: '소속 조직에 배정된 업무를 보고 진행 상태를 바꿉니다.',
  operator: '테넌트 전체 요청·실행을 보고 모니터링을 조회합니다.',
  policy_editor: '자동 처리 정책과 LLM 설정을 바꿉니다.',
  rule_admin: '규칙 학습 후보를 승인하고 규칙을 관리합니다.',
  labeler: '평가 표본에 정답 라벨을 붙입니다.',
  admin: '계정의 역할·소속·원문 열람·사용 여부를 관리합니다.',
};
const nameOf = (u: AdminUser) => u.display_name || u.email || u.user_id;
const state = (u: UserState): UserState => ({ roles: [...u.roles], org_ids: [...u.org_ids], disabled: u.disabled, can_read_source: u.can_read_source });

/** Human-readable difference between two account states, e.g. ["역할 추가: 검토자", "원문 열람 켬"]. */
export function describeChange(before: UserState, after: UserState, orgName: (id: string) => string = (id) => id): string[] {
  const out: string[] = [];
  const list = (label: string, from: string[], to: string[], name: (x: string) => string) => {
    const added = to.filter((x) => !from.includes(x)), removed = from.filter((x) => !to.includes(x));
    if (added.length) out.push(`${label} 추가: ${added.map(name).join(', ')}`);
    if (removed.length) out.push(`${label} 제거: ${removed.map(name).join(', ')}`);
  };
  list('역할', before.roles, after.roles, roleLabel);
  list('조직', before.org_ids, after.org_ids, orgName);
  if (before.can_read_source !== after.can_read_source) out.push(after.can_read_source ? '원문 열람 켬' : '원문 열람 끔');
  if (before.disabled !== after.disabled) out.push(after.disabled ? '계정 사용 중지' : '계정 사용 재개');
  return out;
}

/** 관리자 전용: 같은 테넌트에 계정을 발급하고, 역할·소속·원문 열람·사용 여부를 바꾸며, 사유와 함께 이력을 남긴다. */
export function Admin({ roles = [], selfId = '' }: { roles?: string[]; selfId?: string }) {
  const [data, setData] = useState<{ users: AdminUser[]; orgs: AdminOrg[]; roles: string[] } | null>(null);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [toast, setToast] = useState('');
  const [issuing, setIssuing] = useState(false);
  const isAdmin = roles.includes('admin');
  async function refresh() { try { setData(await userApi.list()); setError(''); return true; } catch (e) { setError((e as ApiError).message); return false; } }
  useEffect(() => { if (isAdmin) void refresh(); }, [isAdmin]);
  const shown = useMemo(() => (data?.users ?? []).filter((u) => (!roleFilter || u.roles.includes(roleFilter))
    && (!query.trim() || `${nameOf(u)} ${u.email ?? ''}`.toLowerCase().includes(query.trim().toLowerCase()))), [data, roleFilter, query]);
  if (!isAdmin) return <section className="admin-page"><header><div><p className="eyebrow">관리</p><h1>권한 관리</h1></div></header>
    <EmptyCard title="관리자 권한이 필요합니다">계정의 역할과 사용 여부는 관리자만 바꿀 수 있습니다. 관리자에게 요청하세요.</EmptyCard></section>;
  const selected = shown.find((u) => u.user_id === selectedId) ?? shown[0] ?? null;
  const users = data?.users ?? [];
  const count = (role: string) => users.filter((u) => u.roles.includes(role)).length;
  return <section className="review-page cases-page admin-page">
    <header><div><p className="eyebrow">관리</p><h1>권한 관리</h1><p>같은 테넌트에 계정을 발급하고 역할·소속 조직·원문 열람·사용 여부를 바꿉니다. 변경은 즉시 적용되고 사유와 함께 기록됩니다.</p></div>
      <div className="admin-head-actions"><Button variant="plain" onClick={() => void refresh()}>새로고침</Button><Button disabled={!data} onClick={() => setIssuing(true)}>새 계정 발급</Button></div></header>
    {error && <p role="alert" className="review-error">{error}</p>}
    {data && <dl className="cases-stats"><div><dt>계정</dt><dd>{users.length}</dd></div><div><dt>관리자</dt><dd>{count('admin')}</dd></div><div><dt>사용 중지</dt><dd>{users.filter((u) => u.disabled).length}</dd></div></dl>}
    {data && <div className="cases-layout">
      <aside className="cases-list admin-list">
        <input className="fld-control admin-search" type="search" aria-label="이름·이메일 검색" placeholder="이름·이메일 검색" value={query} onChange={(e) => setQuery(e.target.value)} />
        <div className="cases-filter" role="group" aria-label="역할 필터">
          <button type="button" aria-pressed={!roleFilter} onClick={() => setRoleFilter('')}>전체 {users.length}</button>
          {data.roles.map((r) => <button key={r} type="button" aria-pressed={roleFilter === r} onClick={() => setRoleFilter(r)}>{roleLabel(r)} {count(r)}</button>)}
        </div>
        {!shown.length && <p className="review-empty-note">조건에 맞는 계정이 없습니다.</p>}
        <ul aria-label="계정 목록">{shown.map((u) => <li key={u.user_id}><button type="button" aria-current={selected?.user_id === u.user_id} onClick={() => setSelectedId(u.user_id)}>
          <span className="admin-row-head"><span className="admin-avatar" aria-hidden="true">{nameOf(u).slice(0, 1)}</span><strong>{nameOf(u)}</strong>{u.user_id === selfId && <span className="admin-self">나</span>}{u.disabled && <StatusBadge status="failure" label="사용 중지" />}</span>
          <small>{u.email}</small>
          <span className="admin-role-pills">{[...u.roles].sort((a, b) => Number(b === 'admin') - Number(a === 'admin')).slice(0, 3).map((r) => <span key={r} className={r === 'admin' ? 'is-admin' : ''}>{roleLabel(r)}</span>)}{u.roles.length > 3 && <span>+{u.roles.length - 3}</span>}</span>
        </button></li>)}</ul>
      </aside>
      {selected && <UserCard key={`${selected.user_id}@${selected.version}`} user={selected} orgs={data.orgs} roles={data.roles} self={selected.user_id === selfId}
        onSaved={async (message, saved) => {
          setToast('');
          if (saved) setData((current) => current && ({ ...current, users: current.users.map((u) => u.user_id === saved.user_id ? saved : u) }));
          const refreshed = await refresh();
          if (saved || refreshed) setToast(message);
        }} />}
    </div>}
    {data && <IssueDialog open={issuing} orgs={data.orgs} roles={data.roles} onClose={() => setIssuing(false)}
      onIssued={async (user) => { await refresh(); setQuery(''); setRoleFilter(''); setSelectedId(user.user_id); }} />}
    <Toast message={toast} onClose={() => setToast('')} />
  </section>;
}

/** One card per role with what it opens; checked cards take the brand tint. */
function RoleCards({ roles, value, onChange, lockAdmin = false }: { roles: string[]; value: string[]; onChange: (next: string[]) => void; lockAdmin?: boolean }) {
  return <div className="admin-roles" role="group" aria-label="역할">{roles.map((r) => {
    const on = value.includes(r), locked = lockAdmin && r === 'admin';
    return <label key={r} className={`admin-role${on ? ' on' : ''}${locked ? ' locked' : ''}`}>
      <input type="checkbox" checked={on} disabled={locked} onChange={(e) => onChange(e.target.checked ? roles.filter((x) => x === r || value.includes(x)) : value.filter((x) => x !== r))} />
      <span className="admin-role-check" aria-hidden="true" />
      <span className="admin-role-text"><strong>{roleLabel(r)}</strong><small>{locked ? '내 계정의 관리자 역할은 뺄 수 없습니다.' : roleHelp[r] ?? r}</small></span>
    </label>;
  })}</div>;
}

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/** 새 계정 발급: 입력 → 서버가 만든 임시 암호를 한 번만 보여 준다(다시 볼 수 없음). */
function IssueDialog({ open, orgs, roles, onClose, onIssued }: { open: boolean; orgs: AdminOrg[]; roles: string[]; onClose: () => void; onIssued: (user: AdminUser) => Promise<void> }) {
  const blank = { email: '', display_name: '', roles: ['requester'], org_ids: orgs.length === 1 ? [orgs[0].id] : [] as string[], can_read_source: false, reason: '' };
  const [form, setForm] = useState(blank);
  const [issued, setIssued] = useState<{ user: AdminUser; temporary_password: string } | null>(null);
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const close = () => { if (saving) return; setForm(blank); setIssued(null); setMessage(''); setCopied(false); onClose(); };
  const problem = !EMAIL.test(form.email.trim()) ? '올바른 이메일을 입력하세요.' : !form.roles.length ? '역할을 하나 이상 고르세요.' : !form.org_ids.length ? '소속 조직을 하나 이상 고르세요.' : !form.reason.trim() ? '발급 사유를 입력하세요.' : '';
  async function submit() {
    setSaving(true); setMessage('');
    try { const result = await userApi.create({ ...form, email: form.email.trim(), display_name: form.display_name.trim() || null, reason: form.reason.trim() }); setIssued(result); await onIssued(result.user); }
    catch (e) { setMessage((e as ApiError).message || '발급하지 못했습니다.'); }
    finally { setSaving(false); }
  }
  async function copy() { try { await navigator.clipboard.writeText(issued!.temporary_password); setCopied(true); } catch { setCopied(false); } }
  return <Modal open={open} title={issued ? '계정을 발급했습니다' : '새 계정 발급'} onClose={close}>
    {issued ? <div className="admin-issued">
      <p>아래 임시 암호를 사용자에게 안전한 경로로 전달하세요. <strong>이 창을 닫으면 다시 볼 수 없습니다.</strong></p>
      <dl className="cases-facts admin-credentials">
        <div><dt>로그인 이메일</dt><dd>{issued.user.email}</dd></div>
        <div><dt>임시 암호</dt><dd><code className="admin-password">{issued.temporary_password}</code></dd></div>
      </dl>
      <div className="review-actions"><Button variant="plain" onClick={() => void copy()}>{copied ? '복사됨' : '암호 복사'}</Button><Button onClick={close}>확인했습니다</Button></div>
    </div> : <form className="admin-issue-form" onSubmit={(e) => { e.preventDefault(); if (!problem && !saving) void submit(); }}>
      <div className="admin-issue-grid">
        <TextField label="이메일" type="email" autoComplete="off" value={form.email} hint="로그인 아이디입니다. 모든 테넌트에서 하나만 쓸 수 있습니다." onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
        <TextField label="이름" value={form.display_name} hint="화면과 이력에 보이는 이름입니다(선택)." onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))} />
      </div>
      <h3>역할</h3>
      <RoleCards roles={roles} value={form.roles} onChange={(next) => setForm((f) => ({ ...f, roles: next }))} />
      <h3>소속 조직</h3>
      <ChipGroup label="검토·업무 배정과 조회 범위가 이 조직을 따릅니다" options={orgs.map((o) => ({ value: o.id, label: o.name }))} value={form.org_ids} onChange={(org_ids) => setForm((f) => ({ ...f, org_ids }))} />
      <Switch label="원문 열람" hint="요청 원문과 근거 발췌를 볼 수 있습니다." checked={form.can_read_source} onChange={(v) => setForm((f) => ({ ...f, can_read_source: v }))} />
      <TextField label="발급 사유" value={form.reason} placeholder="예: 영업팀 신규 입사" onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))} />
      {message && <p role="alert" className="review-error">{message}</p>}
      <div className="review-actions">{problem && <small className="review-why">{problem}</small>}<Button type="button" variant="plain" onClick={close}>취소</Button><Button type="submit" loading={saving} disabled={Boolean(problem) || saving}>발급</Button></div>
    </form>}
  </Modal>;
}

function UserCard({ user, orgs, roles, self, onSaved }: { user: AdminUser; orgs: AdminOrg[]; roles: string[]; self: boolean; onSaved: (message: string, saved?: AdminUser) => Promise<void> }) {
  const [draft, setDraft] = useState<UserState>(() => state(user));
  const [reason, setReason] = useState('');
  const [history, setHistory] = useState<UserHistory[] | null>(null);
  const [historyError, setHistoryError] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  useEffect(() => { let live = true; userApi.detail(user.user_id).then((d) => { if (live) setHistory(d.history); }, (e) => { if (live) setHistoryError((e as ApiError).message || '변경 이력을 불러오지 못했습니다.'); }); return () => { live = false; }; }, [user.user_id, user.version]);
  const orgName = (id: string) => orgs.find((o) => o.id === id)?.name ?? id;
  const changes = describeChange(user, draft, orgName);
  const problem = !draft.roles.length ? '역할을 하나 이상 고르세요.' : !draft.org_ids.length ? '소속 조직을 하나 이상 고르세요.' : !reason.trim() ? '변경 사유를 입력하세요.' : '';
  async function save() {
    setSaving(true); setMessage('');
    try { const saved = await userApi.update(user.user_id, { ...draft, version: user.version, reason: reason.trim() }); await onSaved(`${user.display_name || user.email} 계정을 변경했습니다.`, saved); }
    catch (e) { const err = e as ApiError; setMessage(err.message || '저장하지 못했습니다.'); if (err.status === 409) await onSaved('다른 관리자가 먼저 변경해 최신 상태를 다시 불러왔습니다.'); }
    finally { setSaving(false); }
  }
  return <section className="cases-detail admin-detail" aria-label={`${nameOf(user)} 계정`}>
    <div className="admin-detail-head">
      <span className="admin-avatar is-large" aria-hidden="true">{nameOf(user).slice(0, 1)}</span>
      <div><h2>{nameOf(user)}{self && <span className="admin-self">내 계정</span>}</h2><small>{user.email} · <ShortId id={user.user_id} /> · v{user.version}</small></div>
      <StatusBadge status={user.disabled ? 'failure' : 'success'} label={user.disabled ? '사용 중지' : '사용 중'} />
    </div>

    <h3>역할</h3>
    <p className="admin-note">역할마다 열리는 화면과 동작이 다릅니다. 여러 역할을 함께 줄 수 있습니다.</p>
    <RoleCards roles={roles} value={draft.roles} lockAdmin={self} onChange={(next) => setDraft((d) => ({ ...d, roles: next }))} />

    <h3>소속 조직</h3>
    <ChipGroup label="검토·업무 배정과 조회 범위가 이 조직을 따릅니다" options={orgs.map((o) => ({ value: o.id, label: o.name }))} value={draft.org_ids} onChange={(org_ids) => setDraft((d) => ({ ...d, org_ids }))} />

    <h3>접근</h3>
    <div className="admin-switches">
      <Switch label="원문 열람" hint="요청 원문과 근거 발췌를 볼 수 있습니다. 민감 정보가 포함될 수 있습니다." checked={draft.can_read_source} onChange={(v) => setDraft((d) => ({ ...d, can_read_source: v }))} />
      <Switch label="계정 사용 중지" hint={self ? '내 계정은 사용 중지할 수 없습니다.' : '켜면 즉시 로그아웃되고 다시 로그인할 수 없습니다.'} disabled={self} checked={draft.disabled} onChange={(v) => setDraft((d) => ({ ...d, disabled: v }))} />
    </div>

    <h3>변경 이력</h3>
    {historyError ? <p role="alert" className="review-error">{historyError}</p> : history === null ? <p className="admin-note">불러오는 중…</p> : !history.length ? <p className="admin-note">아직 변경 이력이 없습니다.</p>
      : <ol className="admin-history">{history.map((h) => <li key={h.id}>
        <span>{formatTime(h.at)} · {h.actor_id}</span>
        <strong>{h.action === 'user.create' ? `계정 발급 · ${(h.after?.roles ?? []).map(roleLabel).join(', ')}` : h.before && h.after ? describeChange(h.before, h.after, orgName).join(' · ') || '변경' : h.action}</strong>
        <small>사유: {h.reason}</small>
      </li>)}</ol>}

    <div className={`review-decision admin-decision${changes.length ? ' is-dirty' : ''}`} role="group" aria-label="계정 변경 저장">
      {changes.length > 0 && <ul className="admin-changes" aria-label="바뀔 내용">{changes.map((c) => <li key={c}>{c}</li>)}</ul>}
      <label>변경 사유<textarea value={reason} placeholder="예: 검토 업무 배정, 퇴사로 사용 중지" onChange={(e) => setReason(e.target.value)} /></label>
      {message && <p role="alert" className="review-error">{message}</p>}
      <div className="review-actions">
        {changes.length > 0 && problem && <small className="review-why">{problem}</small>}
        {!changes.length && <small className="review-why">바꿀 항목을 고르면 바뀔 내용이 여기에 보입니다.</small>}
        <Button variant="plain" disabled={!changes.length || saving} onClick={() => { setDraft(state(user)); setReason(''); setMessage(''); }}>되돌리기</Button>
        <Button loading={saving} disabled={!changes.length || Boolean(problem) || saving} onClick={() => void save()}>변경 저장</Button>
      </div>
    </div>
  </section>;
}
