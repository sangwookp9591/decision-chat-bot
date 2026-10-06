import { useEffect, useState } from 'react';
import { NumberField, SearchSelect, Select, Switch } from '../../components/fields';
import { defaultLlmConfig, llmApi, type ConnectionResult, type Models, type ProviderName, type ProviderStatus } from '../../api/llm';
import type { ApiError } from '../../api/client';
import { providerLabel } from '../../lib/assist';
import type { FullPolicyConfig } from './PolicyForm';

type Props = { config: FullPolicyConfig['llm']; canEdit: boolean; onChange: (next: NonNullable<FullPolicyConfig['llm']>) => void };
const features = { summary: '요약 다듬기', task_description: '업무 설명 초안', questions: '부족 정보 질문', rule_explanation: '규칙 후보 설명' };
export function LlmSettings({ config, canEdit, onChange }: Props) {
  const value = config ?? defaultLlmConfig;
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [models, setModels] = useState<Models | null>(null);
  const [error, setError] = useState('');
  const [testing, setTesting] = useState<Partial<Record<ProviderName, boolean>>>({});
  const [results, setResults] = useState<Partial<Record<ProviderName, ConnectionResult>>>({});
  useEffect(() => {
    let live = true;
    llmApi.providers().then((r) => { if (live) setProviders(r.providers); }, (e: ApiError) => { if (live && e.status !== 403) setError(e.message); });
    return () => { live = false; };
  }, []);
  useEffect(() => {
    setModels(null);
    if (!value.provider || !providers.length) return;
    let live = true;
    llmApi.models(value.provider).then((r) => { if (live) { setModels(r); setError(''); } }, (e: ApiError) => { if (live) setError(e.message); });
    return () => { live = false; };
  }, [value.provider, providers]);
  async function test(p: ProviderStatus) {
    setTesting((old) => ({ ...old, [p.provider]: true }));
    try {
      const result = await llmApi.test(p.provider, value.provider === p.provider ? value.model || p.default_model : p.default_model);
      setResults((old) => ({ ...old, [p.provider]: result }));
    } catch (e) { setError((e as ApiError).message); }
    finally { setTesting((old) => ({ ...old, [p.provider]: false })); }
  }
  function select(provider: ProviderName | null) {
    onChange({ ...value, provider, model: provider ? providers.find((p) => p.provider === provider)?.default_model || null : null });
  }
  const selected = providers.find((p) => p.provider === value.provider);
  const choices = models?.models.map((m) => ({ value: m.id, label: `${m.label} · ${m.id}` })) || [];
  if (value.model && !choices.some((m) => m.value === value.model)) choices.push({ value: value.model, label: value.model });
  return <fieldset className="policy-group" aria-label="글쓰기 보조(LLM)"><legend>글쓰기 보조(LLM)</legend>
    <p className="policy-hint">LLM은 요약·업무 설명·질문·규칙 설명 같은 글만 씁니다. 분류·배정·자동 처리에는 쓰이지 않습니다. API 키는 서버 .env에서만 설정합니다.</p>
    {error && <p role="status">{error}</p>}
    {providers.map((p) => { const result = results[p.provider]; return <div className="policy-group" key={p.provider}>
      <strong>{providerLabel[p.provider]}</strong> · 키 {p.key_configured ? '설정됨' : '없음'} · SDK {p.sdk_available ? '사용 가능' : '없음'}
      {canEdit && <button type="button" className="ui-button secondary" disabled={testing[p.provider]} onClick={() => void test(p)} aria-label={`${providerLabel[p.provider]} 연결 테스트`}>연결 테스트</button>}
      <p aria-live="polite">{testing[p.provider] ? '연결 확인 중…' : result ? `${result.ok ? '성공' : '실패'} · ${result.latency_ms}ms · ${new Date(result.tested_at).toLocaleTimeString('ko-KR')} · ${result.message}` : ''}</p>
    </div>; })}
    <Select label="사용할 제공자" disabled={!canEdit || !providers.length} value={value.provider || ''} onChange={(e) => select((e.target.value || null) as ProviderName | null)}>
      <option value="">사용 안 함</option>{Object.entries(providerLabel).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
    </Select>
    {selected && !selected.key_configured && <p role="note">키가 없어 실행 시 기존 방식으로 대체됩니다.</p>}
    {value.provider && <><SearchSelect label="모델" options={choices} value={value.model || ''} disabled={!canEdit || !models} onChange={(model) => onChange({ ...value, model })} />
      {models && <small>{models.source === 'api' ? 'API 목록' : '기본 목록'}</small>}</>}
    {Object.entries(features).map(([key, label]) => <Switch key={key} label={label} disabled={!canEdit} checked={value.features[key as keyof typeof features]} onChange={(on) => onChange({ ...value, features: { ...value.features, [key]: on } })} />)}
    <details><summary>고급: 글쓰기 보조 제한</summary>
      <NumberField label="호출 제한 시간" unit="초" value={value.timeout_seconds} min={1} max={60} disabled={!canEdit} onChange={(timeout_seconds) => onChange({ ...value, timeout_seconds })} />
      <NumberField label="단계 예산" unit="초" value={value.step_budget_seconds} min={1} max={90} disabled={!canEdit} onChange={(step_budget_seconds) => onChange({ ...value, step_budget_seconds })} />
      <NumberField label="최대 출력 토큰" value={value.max_output_tokens} min={256} max={8000} disabled={!canEdit} onChange={(max_output_tokens) => onChange({ ...value, max_output_tokens })} />
    </details>
  </fieldset>;
}
