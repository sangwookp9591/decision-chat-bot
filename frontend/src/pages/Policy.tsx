import { useCallback, useEffect, useState } from 'react';
import { DataTable, ErrorState, LoadingState, StatusBadge } from '../components';
import { policyApi, type PolicyConfig, type PolicyDetail, type PolicyVersion } from '../api/policy';
import { policyFieldLabel } from '../lib/labels';
import { EventConnectionStatus, useEventStream } from '../state/events';
import type { ApiError } from '../api/client';
import { localizeError } from '../components/statusLabels';
import './policy/policy.css';

const defaults: PolicyConfig = { schema_version: 'policy-schema-v1', auto_assign: false, choice_confidence_thresholds: {}, noul_probability_thresholds: {}, risk_clear_max: .2, reviewer_groups: {}, limits: {}, evidence_noul_threshold: .6, catalog_noul_threshold: .6, feature_flags: {}, rules: [] };
const protectedFields = new Set(['schema_version', 'auto_assign', 'rules']);
const pretty = (value: unknown) => JSON.stringify(value, null, 2);
function PolicyButton({ children, variant = 'primary', ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' }) { return <button {...props} className={`ui-button ${variant} ${props.className || ''}`}>{children}</button>; }

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
  const refresh = useCallback(async () => { try { const [active, history] = await Promise.all([policyApi.active(), policyApi.versions()]); setActiveVersion(active.version); setConfig(active.config); setDrafts({}); setFieldErrors({}); setVersions(history.versions); setError(''); } catch (e) { setError((e as ApiError).message || '정책을 불러오지 못했습니다.'); } finally { setLoading(false); } }, []);
  const onEvent = useCallback((event: {type:string}) => { if (event.type === 'policy.published') void refresh(); }, [refresh]);
  const stream = useEventStream({}, undefined, onEvent);
  useEffect(() => { void refresh(); }, [refresh]);
  if (loading) return <LoadingState label="정책 불러오는 중" />;
  if (error) return <ErrorState title="정책을 불러오지 못했습니다" onRetry={() => { setLoading(true); void refresh(); }}>{error}</ErrorState>;

  async function chooseVersion(row: PolicyVersion) { try { setSelected(await policyApi.version(row.version)); } catch (e) { setNotice((e as ApiError).message || '버전을 불러오지 못했습니다.'); } }
  function updateField(key: keyof PolicyConfig, value: string) {
    setDrafts((current) => ({ ...current, [key]: value }));
    try { const parsed: unknown = JSON.parse(value); setConfig((current) => ({ ...current, [key]: parsed })); setFieldErrors(({ [key]: _gone, ...rest }) => rest); setValidation(null); }
    catch { setFieldErrors((current) => ({ ...current, [key]: `${key}: 올바른 JSON 값이 아닙니다. 마지막으로 유효했던 값이 유지됩니다.` })); setValidation(null); }
  }
  async function validateDraft() { setSaving(true); try { const result = await policyApi.validate(config); setValidation(result); } catch (e) { setNotice((e as ApiError).message || '검증 요청에 실패했습니다.'); } finally { setSaving(false); } }
  async function mutate(work: () => Promise<PolicyDetail>, fallback: string, after: (result: PolicyDetail) => void) {
    setSaving(true); setNotice('');
    try {
      const result = await work();
      setActiveVersion(result.version); setConfig(result.config); setDrafts({}); setFieldErrors({}); setReason(''); after(result); await refresh();
    } catch (e) {
      const apiError = e as ApiError;
      setNotice(apiError.status === 409 ? `활성 버전이 변경되었습니다. 최신 버전을 다시 불러왔습니다. (${apiError.message})` : apiError.message || fallback);
      if (apiError.status === 409) await refresh();
    } finally { setSaving(false); }
  }
  async function publishDraft() {
    if (!reason.trim()) { setNotice('게시 사유를 입력해 주세요.'); return; }
    if (fieldError) return;
    await mutate(() => policyApi.publish(config, reason, activeVersion), '게시하지 못했습니다.', (result) => { setValidation(null); setNotice(`정책 버전 ${result.version}을 게시했습니다.`); });
  }
  async function rollback() {
    if (!selected) return;
    if (!reason.trim()) { setNotice('되돌리기 사유를 입력해 주세요.'); return; }
    const targetVersion = selected.version;
    await mutate(() => policyApi.rollback(targetVersion, reason, activeVersion), '되돌리지 못했습니다.', (result) => { setSelected(null); setNotice(`버전 ${targetVersion} 기준 새 정책 버전 ${result.version}을 만들었습니다.`); });
  }
  const columns = [
    { key: 'version' as const, label: '버전', render: (v: PolicyVersion) => <button type="button" onClick={() => void chooseVersion(v)}>v{v.version}</button> },
    { key: 'created_by' as const, label: '작성자' }, { key: 'reason' as const, label: '사유' }, { key: 'created_at' as const, label: '시각' },
    { key: 'status' as const, label: '상태', render: (v: PolicyVersion) => <StatusBadge status={v.status === 'active' ? 'success' : 'pending'} label={v.status === 'active' ? '활성' : '이전 버전'} /> },
  ];
  return <section className="policy-page"><p className="eyebrow">JEV TRIAGE</p><header className="policy-heading"><div><h1>정책</h1><p>활성 버전 <strong>v{activeVersion}</strong> · 진행 중 실행은 시작 시 고정한 정책 버전을 사용합니다.</p></div><EventConnectionStatus status={stream.status} /></header>
    <div className="policy-safety"><strong>잠금 · 필수 검토</strong><span>임상·안전·규제·긴급 검토는 항상 필요하며 편집할 수 없습니다.</span><strong>잠금 · 무승인 배정 금지</strong><span>승인 없이 업무를 배정하는 설정은 허용되지 않습니다.</span></div>
    <div className="policy-grid"><section className="policy-card"><h2>정책 편집기</h2>{!canEdit && <p role="note">정책 편집자 권한이 없어 읽기 전용입니다.</p>}
      {Object.entries(config).map(([key, value]) => <label className="policy-field" key={key}><span>{policyFieldLabel(key)}{protectedFields.has(key) && <small> · 잠금 / 읽기 전용</small>}</span><textarea aria-label={policyFieldLabel(key)} readOnly={!canEdit || protectedFields.has(key)} value={drafts[key] ?? pretty(value)} aria-invalid={Boolean(fieldErrors[key])} rows={Math.min(8, Math.max(2, (drafts[key] ?? pretty(value)).split('\n').length))} onChange={(e) => updateField(key as keyof PolicyConfig, e.target.value)} /></label>)}
      <p>rules 필드는 규칙 학습 화면에서 관리합니다.</p>{Object.entries(fieldErrors).map(([key, message]) => <p key={key} role="alert">{message}</p>)}
      <div className="policy-actions"><PolicyButton variant="secondary" disabled={saving} onClick={() => void validateDraft()}>서버 검증</PolicyButton>{canEdit && <PolicyButton disabled={saving || !validation?.valid || !!fieldError} onClick={() => void publishDraft()}>게시</PolicyButton>}</div>
      {validation && <div role={validation.valid ? 'status' : 'alert'}><strong>{validation.valid ? '검증 통과' : '검증 오류'}</strong>{!validation.valid && <ul>{validation.errors.map((item, i) => <li key={`${item.code}-${i}`}>{localizeError(`${item.code}: ${item.reason}`)}<details><summary>기술 상세</summary><code>{item.code}: {item.reason}</code></details></li>)}</ul>}</div>}
      <label className="policy-field"><span>{selected ? `되돌리기 사유 (v${selected.version} 기준)` : '게시 사유 (필수)'}</span><input value={reason} onChange={(e) => setReason(e.target.value)} disabled={!canEdit} /></label>
      {selected && canEdit && <PolicyButton variant="secondary" disabled={saving} onClick={() => void rollback()}>선택 버전 기준으로 되돌리기</PolicyButton>}
      {notice && <p role="status">{notice}</p>}
    </section><section className="policy-card"><h2>버전 이력</h2><DataTable columns={columns} rows={versions} getRowKey={(row) => String(row.version)} caption="정책 버전 이력" />{selected && <div className="policy-diff"><h3>v{selected.version} diff</h3>{Object.keys(selected.diff).length ? Object.entries(selected.diff).map(([key, diff]) => <article key={key}><h4>{policyFieldLabel(key)}</h4><pre>{pretty(diff.before)} → {pretty(diff.after)}</pre></article>) : <p>변경 항목이 없습니다.</p>}</div>}</section></div>
  </section>;
}
