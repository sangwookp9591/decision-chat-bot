import { LlmSettings } from './policy/LlmSettings';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Button, DataTable, ErrorState, LoadingState, StatusBadge } from '../components';
import { PolicyForm, policyHint, policyLabel, type FullPolicyConfig } from './policy/PolicyForm';
import { formatTime } from '../lib/format';
import { policyApi, type PolicyConfig, type PolicyDetail, type PolicyVersion } from '../api/policy';
import { EventConnectionStatus, useEventStream, type StreamEvent } from '../state/events';
import type { ApiError } from '../api/client';
import { localizeError } from '../components/statusLabels';
import './policy/policy.css';

const defaults: PolicyConfig = { schema_version: 'policy-schema-v1', auto_assign: false, choice_confidence_thresholds: {}, noul_probability_thresholds: {}, risk_clear_max: .2, reviewer_groups: {}, limits: {}, evidence_noul_threshold: .6, catalog_noul_threshold: .6, feature_flags: {}, rules: [] };
const protectedFields = new Set(['schema_version', 'auto_assign', 'rules']);
const pretty = (value: unknown) => JSON.stringify(value, null, 2);
const PolicyButton = Button;
/** Narrow screens swap the history table for a card list (a 5-column table cannot fit 375px). */
function useNarrow(query = '(max-width: 520px)') {
  const [narrow, setNarrow] = useState(() => typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia(query).matches);
  useEffect(() => { if (typeof window.matchMedia !== 'function') return; const mq = window.matchMedia(query); const on = () => setNarrow(mq.matches); on(); mq.addEventListener?.('change', on); return () => mq.removeEventListener?.('change', on); }, [query]);
  return narrow;
}

export function Policy({ canEdit = false }: { canEdit?: boolean }) {
  const [activeVersion, setActiveVersion] = useState(0);
  const [config, setConfig] = useState<PolicyConfig>(defaults);
  const [versions, setVersions] = useState<PolicyVersion[]>([]);
  const [selected, setSelected] = useState<PolicyDetail | null>(null);
  const [reason, setReason] = useState('');
  const [validation, setValidation] = useState<{ errors: Array<{code:string;reason:string}>; valid: boolean } | null>(null);
  // Raw text per field: typing may pass through invalid JSON; config only ever holds the last valid value.
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const fieldError = Object.values(fieldErrors)[0] || '';
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [incoming, setIncoming] = useState<number | null>(null);
  // Synchronous mirrors of state: events and clicks can land between a keystroke and the next render.
  const configRef = useRef(config); const dirtyRef = useRef(false); const activeRef = useRef(0); const loadedRef = useRef(false); const generation = useRef(0);
  /** Apply the server's active policy. Unless `force`, an edit in progress is kept and only the history updates. */
  const refresh = useCallback(async (force = false) => {
    const mine = ++generation.current;
    try {
      const [active, history] = await Promise.all([policyApi.active(), policyApi.versions()]);
      if (mine !== generation.current) return; // a newer fetch started: this answer is stale
      const keepEdits = !force && dirtyRef.current;
      activeRef.current = active.version; setActiveVersion(active.version); setVersions(history.versions);
      if (keepEdits) setIncoming(active.version);
      else { configRef.current = active.config; dirtyRef.current = false; setConfig(active.config); setDrafts({}); setFieldErrors({}); setIncoming(null); }
      loadedRef.current = true; setError('');
    } catch (e) { if (mine === generation.current) setError((e as ApiError).message || '정책을 불러오지 못했습니다.'); } finally { if (mine === generation.current) setLoading(false); }
  }, []);
  // A new session replays old policy.published events: only a version above the one on screen is news.
  const onEvent = useCallback((event: StreamEvent) => {
    if (event.type !== 'policy.published' || !loadedRef.current) return;
    const version = Number(event.payload?.version);
    if (Number.isFinite(version) && version <= activeRef.current) return;
    if (dirtyRef.current) setIncoming(Number.isFinite(version) ? version : activeRef.current + 1); else void refresh();
  }, [refresh]);
  const stream = useEventStream({}, undefined, onEvent);
  useEffect(() => { void refresh(); }, [refresh]);
  const narrow = useNarrow();
  if (loading) return <LoadingState label="정책 불러오는 중" />;
  if (error) return <ErrorState title="정책을 불러오지 못했습니다" onRetry={() => { setLoading(true); void refresh(true); }}>{error}</ErrorState>;

  async function chooseVersion(row: PolicyVersion) { try { setSelected(await policyApi.version(row.version)); } catch (e) { setNotice((e as ApiError).message || '버전을 불러오지 못했습니다.'); } }
  function updateField(key: keyof PolicyConfig, value: string) {
    dirtyRef.current = true; setDrafts((current) => ({ ...current, [key]: value }));
    try { const parsed: unknown = JSON.parse(value); configRef.current = { ...configRef.current, [key]: parsed }; setConfig(configRef.current); setFieldErrors(({ [key]: _gone, ...rest }) => rest); setValidation(null); }
    catch { setFieldErrors((current) => ({ ...current, [key]: `${policyLabel(key)}: 올바른 JSON 값이 아닙니다. 마지막으로 유효했던 값이 유지됩니다.` })); setValidation(null); }
  }
  /** Form edit: replace one nested value, keep the rest, and drop the JSON draft of that top-level key. */
  function setPath(path: Array<string | number>, value: unknown) {
    const [key, ...rest] = path as [string, ...Array<string | number>];
    const assign = (node: any, steps: Array<string | number>): any => {
      if (!steps.length) return value;
      const copy = Array.isArray(node) ? [...node] : { ...(node ?? {}) };
      copy[steps[0] as any] = assign(copy[steps[0] as any], steps.slice(1));
      return copy;
    };
    dirtyRef.current = true;
    configRef.current = { ...configRef.current, [key]: assign((configRef.current as any)[key], rest) };
    setConfig(configRef.current); setValidation(null);
    setDrafts(({ [key]: _gone, ...others }) => others); setFieldErrors(({ [key]: _g, ...others }) => others);
  }
  function markInvalid(path: string, on: boolean) { setFieldErrors((current) => { const id = `form:${path}`; if (on) return { ...current, [id]: `${path}: 숫자를 입력해 주세요.` }; const { [id]: _gone, ...rest } = current; return rest; }); setValidation(null); }
  async function validateDraft() { setSaving(true); try { const result = await policyApi.validate(configRef.current); setValidation(result); } catch (e) { setNotice((e as ApiError).message || '검증 요청에 실패했습니다.'); } finally { setSaving(false); } }
  async function mutate(work: () => Promise<PolicyDetail>, fallback: string, after: (result: PolicyDetail) => void) {
    setSaving(true); setNotice('');
    try {
      const result = await work();
      activeRef.current = result.version; configRef.current = result.config; dirtyRef.current = false; setActiveVersion(result.version); setConfig(result.config); setDrafts({}); setFieldErrors({}); setIncoming(null); setReason(''); after(result); await refresh(true);
    } catch (e) {
      const apiError = e as ApiError;
      setNotice(apiError.status === 409 ? `활성 버전이 변경되었습니다. 최신 버전을 다시 불러왔습니다. (${apiError.message})` : apiError.message || fallback);
      if (apiError.status === 409) await refresh(true);
    } finally { setSaving(false); }
  }
  async function publishDraft() {
    if (!reason.trim()) { setNotice('게시 사유를 입력해 주세요.'); return; }
    if (fieldError) return;
    await mutate(() => policyApi.publish(configRef.current, reason, activeVersion), '게시하지 못했습니다.', (result) => { setValidation(null); setNotice(`정책 버전 ${result.version}을 게시했습니다.`); });
  }
  async function rollback() {
    if (!selected) return;
    if (!reason.trim()) { setNotice('되돌리기 사유를 입력해 주세요.'); return; }
    const targetVersion = selected.version;
    await mutate(() => policyApi.rollback(targetVersion, reason, activeVersion), '되돌리지 못했습니다.', (result) => { setSelected(null); setNotice(`버전 ${targetVersion} 기준 새 정책 버전 ${result.version}을 만들었습니다.`); });
  }
  const columns = [
    { key: 'version' as const, label: '버전', render: (v: PolicyVersion) => <button type="button" className="policy-version-link" onClick={() => void chooseVersion(v)}>v{v.version}</button> },
    { key: 'created_by' as const, label: '작성자' }, { key: 'reason' as const, label: '사유' }, { key: 'created_at' as const, label: '시각', render: (v: PolicyVersion) => formatTime(v.created_at) },
    { key: 'status' as const, label: '상태', render: (v: PolicyVersion) => <StatusBadge status={v.status === 'active' ? 'success' : 'pending'} label={v.status === 'active' ? '활성' : '이전 버전'} /> },
  ];
  const hasFormError = Object.keys(fieldErrors).length > 0;
  const publishBlock = !canEdit ? '' : fieldError || hasFormError ? '입력 오류를 고친 뒤 다시 검증해 주세요.' : !validation ? '값을 바꾸거나 처음 열었다면 먼저 ‘서버 검증’을 통과해야 게시할 수 있습니다.' : !validation.valid ? '검증 오류를 해결하고 다시 검증해 주세요.' : '';
  const globalErrors = Object.entries(fieldErrors).filter(([key]) => !key.startsWith('form:'));
  const full = config as FullPolicyConfig;
  return <section className="policy-page"><header className="policy-heading"><div><h1>정책</h1><p>활성 버전 <strong>v{activeVersion}</strong> · 진행 중 실행은 시작 시 고정한 정책 버전을 사용합니다.</p></div><EventConnectionStatus status={stream.status} /></header>
    <div className="policy-safety"><strong>잠금 · 필수 검토</strong><span>임상·안전·규제·긴급 검토는 항상 필요하며 편집할 수 없습니다.</span><strong>잠금 · 무승인 배정 금지</strong><span>승인 없이 업무를 배정하는 설정은 허용되지 않습니다.</span></div>
    <div className="policy-grid"><section className="policy-card"><h2>정책 편집기</h2>{!canEdit && <p role="note">정책 편집자 권한이 없어 읽기 전용입니다.</p>}
      {incoming !== null && <div className="policy-incoming" role="status"><strong>새 버전 v{incoming}이 게시되었습니다.</strong><span>편집 중인 값은 아직 그대로입니다. 새 버전을 반영하면 지금 편집한 내용은 사라집니다.</span><PolicyButton variant="secondary" onClick={() => void refresh(true)}>새 버전 반영</PolicyButton><PolicyButton variant="plain" onClick={() => setIncoming(null)}>내 편집 유지</PolicyButton></div>}
      <LlmSettings config={full.llm} canEdit={canEdit} onChange={(next) => setPath(['llm'], next)} />
      <PolicyForm config={full} readOnly={!canEdit} set={setPath} invalid={markInvalid} />
      <details className="policy-advanced"><summary>고급: JSON 보기</summary>
        <p className="policy-hint">항목별 원본 값입니다. 위 입력란에 없는 항목(예: 새 검토자 그룹)은 여기서 고칩니다. 잘못된 JSON은 마지막으로 유효했던 값이 유지됩니다.</p>
        {Object.entries(config).map(([key, value]) => { const text = drafts[key] ?? pretty(value); return <div className="policy-field" key={key}><label><span>{policyLabel(key)}{protectedFields.has(key) && <small> · 잠금 / 읽기 전용</small>}</span>{policyHint(key) && <small className="policy-hint">{policyHint(key)}</small>}<textarea aria-label={`${policyLabel(key)} (JSON)`} readOnly={!canEdit || protectedFields.has(key)} value={text} aria-invalid={Boolean(fieldErrors[key])} rows={Math.min(8, Math.max(2, text.split('\n').length))} onChange={(e) => updateField(key as keyof PolicyConfig, e.target.value)} /></label><code className="policy-key">{key}</code></div>; })}
      </details>
      <p className="policy-note">rules 필드는 규칙 학습 화면에서 관리합니다.</p>{globalErrors.map(([key, message]) => <p key={key} role="alert" className="policy-error">{message}</p>)}
      <div className="policy-actions"><PolicyButton variant="secondary" disabled={saving} onClick={() => void validateDraft()}>서버 검증</PolicyButton>{canEdit && <PolicyButton disabled={saving || !validation?.valid || hasFormError} aria-describedby={publishBlock ? 'policy-publish-why' : undefined} onClick={() => void publishDraft()}>게시</PolicyButton>}</div>
      {publishBlock && <small id="policy-publish-why" className="policy-why">게시할 수 없는 이유: {publishBlock}</small>}
      {validation && <div role={validation.valid ? 'status' : 'alert'} className={validation.valid ? 'policy-valid' : 'policy-invalid'}><strong>{validation.valid ? '검증 통과' : '검증 오류'}</strong>{!validation.valid && <ul>{validation.errors.map((item, i) => <li key={`${item.code}-${i}`}>{localizeError(`${item.code}: ${item.reason}`)}<details><summary>기술 상세</summary><code>{item.code}: {item.reason}</code></details></li>)}</ul>}</div>}
      <label className="policy-field"><span>{selected ? `되돌리기 사유 (v${selected.version} 기준)` : '게시 사유 (필수)'}</span><input value={reason} onChange={(e) => setReason(e.target.value)} disabled={!canEdit} /></label>
      {selected && canEdit && <PolicyButton variant="secondary" disabled={saving} onClick={() => void rollback()}>선택 버전 기준으로 되돌리기</PolicyButton>}
      {notice && <p role="status">{notice}</p>}
    </section><section className="policy-card"><h2>버전 이력</h2>
      {narrow ? <ul className="policy-version-cards" aria-label="정책 버전 이력">{versions.map((v) => <li key={v.version}><div><button type="button" className="policy-version-link" onClick={() => void chooseVersion(v)}>v{v.version}</button><StatusBadge status={v.status === 'active' ? 'success' : 'pending'} label={v.status === 'active' ? '활성' : '이전 버전'} /></div><p>{v.reason || '사유 없음'}</p><small>{v.created_by} · {formatTime(v.created_at)}</small></li>)}</ul>
        : <div className="policy-table"><DataTable columns={columns} rows={versions} getRowKey={(row) => String(row.version)} caption="정책 버전 이력" /></div>}
      {selected && <div className="policy-diff"><h3>v{selected.version} diff</h3>{Object.keys(selected.diff).length ? Object.entries(selected.diff).map(([key, diff]) => <article key={key}><h4>{policyLabel(key)}</h4><pre>{pretty(diff.before)} → {pretty(diff.after)}</pre></article>) : <p>변경 항목이 없습니다.</p>}</div>}</section></div>
  </section>;
}
