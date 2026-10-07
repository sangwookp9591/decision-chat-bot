import { useCallback, useEffect, useState } from 'react';
import { Modal, Toast } from '../../components';
import { NumberField, SearchSelect, Select, Switch } from '../../components/fields';
import { defaultLlmConfig, llmApi, type ChatgptStatus, type ConnectionResult, type Models, type ProviderName, type ProviderStatus } from '../../api/llm';
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
  const [chatgpt, setChatgpt] = useState<ChatgptStatus | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [toast, setToast] = useState('');
  const [welcome, setWelcome] = useState(false);
  const closeToast = useCallback(() => setToast(''), []);
  const [testing, setTesting] = useState<Partial<Record<ProviderName, boolean>>>({});
  const [results, setResults] = useState<Partial<Record<ProviderName, ConnectionResult>>>({});
  useEffect(() => {
    let live = true;
    llmApi.providers().then((r) => { if (live) setProviders(r.providers); }, (e: ApiError) => { if (live && e.status !== 403) setError(e.message); });
    return () => { live = false; };
  }, []);
  useEffect(() => {
    if (!providers.some((p) => p.provider === 'chatgpt')) return;
    let live = true;
    llmApi.chatgptStatus().then((r) => { if (live) setChatgpt(r); }, (e: ApiError) => { if (live) setError(e.message); });
    return () => { live = false; };
  }, [providers]);
  useEffect(() => {
    const url = new URL(window.location.href);
    const result = url.searchParams.get('chatgpt');
    if (!result) return;
    const messages: Record<string, string> = {
      ok: 'ChatGPT 연결이 완료되었습니다.', PLAN_USAGE_NOT_GRANTED: '로그인했지만 요금제 사용이 허용되지 않았습니다. 다시 연결해 권한을 허용하세요.',
      CONSENT_DENIED: 'ChatGPT 연결을 취소했습니다.', STATE_INVALID: '연결 요청이 만료되었거나 이미 사용되었습니다. 다시 연결하세요.',
    };
    setToast(messages[result] || 'ChatGPT 연결에 실패했습니다. 다시 연결하세요.');
    setWelcome(result === 'ok' && url.searchParams.get('chatgpt_welcome') === '1');
    url.searchParams.delete('chatgpt');
    url.searchParams.delete('chatgpt_welcome');
    window.history.replaceState(null, '', url);
  }, []);
  async function connectChatgpt() {
    setConnecting(true);
    try { const result = await llmApi.chatgptConnect(); window.location.assign(result.authorize_url); }
    catch (e) { setError((e as ApiError).message); setConnecting(false); }
  }
  async function disconnectChatgpt() {
    setConnecting(true);
    try {
      const result = await llmApi.chatgptDisconnect();
      setChatgpt(await llmApi.chatgptStatus());
      setResults((old) => ({ ...old, chatgpt: undefined }));
      setModels(null);
      setToast(result.remote_revocation_confirmed ? 'ChatGPT 연결을 해제했습니다.' : '로컬 연결을 해제했습니다. 원격 해제는 확인되지 않았으니 ChatGPT 설정에서 앱을 해제하세요.');
    } catch (e) { setError((e as ApiError).message); }
    finally { setConnecting(false); }
  }
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
      let model = value.provider === p.provider ? value.model || p.default_model : p.default_model;
      if (p.provider === 'chatgpt' && !model) model = (await llmApi.models('chatgpt')).models[0]?.id || '';
      if (!model) { setError('사용 가능한 ChatGPT 모델이 없습니다. 연결과 요금제 사용 권한을 확인하세요.'); return; }
      const result = await llmApi.test(p.provider, model);
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
    <p className="policy-hint">LLM은 요약·업무 설명·질문·규칙 설명 같은 글만 씁니다. 분류·배정·자동 처리에는 쓰이지 않습니다. API 키는 서버 .env에서 설정하며, ChatGPT 구독은 로그인으로 연결합니다.</p>
    <Toast message={toast} onClose={closeToast} />
    <Modal open={welcome} title="ChatGPT 요금제를 사용합니다" onClose={() => setWelcome(false)}><p>일동이의 지원되는 AI 요청은 ChatGPT 요금제 사용량을 사용합니다. ChatGPT 설정 → 사용량에서 관리할 수 있습니다.</p><button type="button" className="ui-button" onClick={() => setWelcome(false)}>확인</button></Modal>
    {error && <p role="status">{error}</p>}
    {providers.map((p) => { const result = results[p.provider]; return <div className="policy-group" key={p.provider}>
      <strong>{providerLabel[p.provider]}</strong>{p.provider === 'chatgpt' ? <>
        <span> · {chatgpt ? chatgpt.connected ? '연결됨' : '연결 안 됨' : '상태 확인 중…'}</span>
        {chatgpt?.connected && <p>{chatgpt.email} · 요금제 사용 {chatgpt.plan_usage_granted ? '허용됨' : '허용 안 됨'} · 연결한 정책 편집자: {chatgpt.connected_by} ({chatgpt.connected_tenant})</p>}
        <p className="policy-hint">이 로컬 설치 전체가 하나의 ChatGPT 연결을 공유합니다. 지원되는 글쓰기 보조 요청에 ChatGPT 요금제를 사용합니다.</p>
        <a href="https://chatgpt.com/settings/usage" target="_blank" rel="noreferrer">ChatGPT 사용량 관리</a>
        {canEdit && <>
          <button type="button" className="ui-button secondary" disabled={connecting || !chatgpt} onClick={() => void connectChatgpt()}>Continue with ChatGPT</button>
          {chatgpt?.connected && <button type="button" className="ui-button secondary" disabled={connecting} onClick={() => void disconnectChatgpt()}>연결 해제</button>}
        </>}
      </> : <> · 키 {p.key_configured ? '설정됨' : '없음'} · SDK {p.sdk_available ? '사용 가능' : '없음'}</>}
      {canEdit && <button type="button" className="ui-button secondary" disabled={testing[p.provider] || (p.provider === 'chatgpt' && (!chatgpt?.connected || !chatgpt?.plan_usage_granted || connecting))} onClick={() => void test(p)} aria-label={`${providerLabel[p.provider]} 연결 테스트`}>연결 테스트</button>}
      <p aria-live="polite">{testing[p.provider] ? '연결 확인 중…' : result ? `${result.ok ? '성공' : '실패'} · ${result.latency_ms}ms · ${new Date(result.tested_at).toLocaleTimeString('ko-KR')} · ${result.message}` : ''}</p>
    </div>; })}
    <Select label="사용할 제공자" disabled={!canEdit || !providers.length} value={value.provider || ''} onChange={(e) => select((e.target.value || null) as ProviderName | null)}>
      <option value="">사용 안 함</option>{Object.entries(providerLabel).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
    </Select>
    {selected && (selected.provider === 'chatgpt' ? !chatgpt?.plan_usage_granted : !selected.key_configured) && <p role="note">인증 또는 사용 권한이 없어 실행 시 기존 방식으로 대체됩니다.</p>}
    {value.provider && <><SearchSelect label="모델" options={choices} value={value.model || ''} disabled={!canEdit || !models} onChange={(model) => onChange({ ...value, model })} />
      {models && <small>{models.source === 'api' ? 'API 목록' : '기본 목록'}</small>}</>}
    {Object.entries(features).map(([key, label]) => <Switch key={key} label={label} disabled={!canEdit} checked={value.features[key as keyof typeof features]} onChange={(on) => onChange({ ...value, features: { ...value.features, [key]: on } })} />)}
    <details><summary>고급: 글쓰기 보조 제한</summary>
      <NumberField label="호출 제한 시간" unit="초" value={value.timeout_seconds} min={1} max={60} disabled={!canEdit} onChange={(timeout_seconds) => onChange({ ...value, timeout_seconds })} />
      <NumberField label="단계 예산" unit="초" value={value.step_budget_seconds} min={1} max={90} disabled={!canEdit} onChange={(step_budget_seconds) => onChange({ ...value, step_budget_seconds })} />
      {value.provider === 'chatgpt' && <p className="policy-hint">ChatGPT 프리뷰에서는 최대 출력 토큰 설정을 지원하지 않습니다. 응답은 로컬 형식 검증을 거칩니다.</p>}
      <NumberField label="최대 출력 토큰" value={value.max_output_tokens} min={256} max={8000} disabled={!canEdit || value.provider === 'chatgpt'} onChange={(max_output_tokens) => onChange({ ...value, max_output_tokens })} />
    </details>
  </fieldset>;
}
