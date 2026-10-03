import { useState } from 'react';
import type { RuleScope } from '../../api/learning';
import { RULE_ID_PATTERN, type ActionKey, type ActionState } from './learningModel';

export type ActionHandlers = {
  approve: (ruleId: string, reason: string, scope?: RuleScope, acknowledgeInsufficient?: boolean) => void;
  reject: (reason: string) => void;
  validate: (range: { from: string; to: string; max_calls?: number }) => void;
  markValidated: (reason: string) => void;
  publish: (reason: string) => void;
  stop: (reason: string) => void;
  revert: (toVersion: number, reason: string) => void;
};
type Props = {
  states: Record<ActionKey, ActionState>; isAdmin: boolean; busy: boolean; handlers: ActionHandlers;
  defaultRuleId: string; defaultScope: RuleScope; revertTargets: number[]; showDecision: boolean; showVersion: boolean;
  requiresInsufficientAck?: boolean;
  retryDecision?: string | null;
};
const day = (offset: number) => new Date(Date.now() + offset * 86_400_000).toISOString().slice(0, 16);

export function Actions({ states, isAdmin, busy, handlers, defaultRuleId, defaultScope, revertTargets, showDecision, showVersion, requiresInsufficientAck = false, retryDecision }: Props) {
  const [reason, setReason] = useState('');
  const [ruleId, setRuleId] = useState(defaultRuleId);
  const [scopeText, setScopeText] = useState(JSON.stringify(defaultScope, null, 2));
  const [scopeError, setScopeError] = useState('');
  const [from, setFrom] = useState(day(-30));
  const [to, setTo] = useState(day(1));
  const [maxCalls, setMaxCalls] = useState('');
  const [target, setTarget] = useState<number | ''>(revertTargets[0] ?? '');
  const hasReason = reason.trim().length > 0;
  const sufficientReason = reason.trim().length >= 10;
  const [acknowledgeInsufficient, setAcknowledgeInsufficient] = useState(false);
  const ruleIdOk = RULE_ID_PATTERN.test(ruleId);
  const gate = (key: ActionKey, extra = true, extraWhy = '') => ({
    disabled: busy || !states[key].enabled || !extra,
    title: states[key].reason || (!extra ? extraWhy : undefined),
  });
  const why = (key: ActionKey, extra = true, extraWhy = '') => states[key].reason || (!extra ? extraWhy : null);
  const needReason = '사유를 입력해 주세요.';
  function approveWithScope() {
    try {
      const parsed = JSON.parse(scopeText) as RuleScope;
      if (!parsed || !Array.isArray(parsed.all)) throw new Error('scope');
      setScopeError(''); handlers.approve(ruleId, reason.trim(), parsed, acknowledgeInsufficient);
    } catch { setScopeError('범위는 {"all": [조건...]} 형식의 JSON이어야 합니다.'); }
  }
  const row = (key: ActionKey, label: string, onClick: () => void, extra = true, extraWhy = '', variant = 'secondary') => {
    const reasonText = why(key, extra, extraWhy);
    return <div className="learning-action" key={key}><button type="button" className={`ui-button ${variant}`} {...gate(key, extra, extraWhy)} onClick={onClick}>{label}</button>{reasonText && <small role="note">비활성: {reasonText}</small>}</div>;
  };
  return <section className="learning-card" aria-label="규칙 동작">
    <h3>동작</h3>
    <p className="learning-hint">후보 제안은 검토자 이상, 승인·기각·검증·게시·중단·되돌리기는 규칙 관리자만 할 수 있으며 각각 감사 기록이 남습니다. <strong>요청 한 건의 수정 승인은 규칙 게시가 아닙니다.</strong></p>
    {!isAdmin && <p role="note" className="learning-caution">현재 역할은 규칙 관리자가 아니므로 모든 동작 버튼이 비활성입니다.</p>}
    <label className="learning-field">사유 (필수){requiresInsufficientAck && <small>자료 부족 승인에는 10자 이상 입력해야 합니다.</small>}<input aria-label="결정 사유" value={reason} onChange={(e) => setReason(e.target.value)} /></label>
    {requiresInsufficientAck && <label className="learning-field"><input type="checkbox" aria-label="자료 부족 상태임을 확인" checked={acknowledgeInsufficient} onChange={(e) => setAcknowledgeInsufficient(e.target.checked)} /> 자료 부족 상태임을 확인</label>}
    {showDecision && <>
      <label className="learning-field">규칙 ID<input aria-label="규칙 ID" className="mono" value={ruleId} onChange={(e) => setRuleId(e.target.value.trim())} aria-invalid={!ruleIdOk} />{!ruleIdOk && <small role="alert">형식: R-영문대문자_-숫자2자리 이상 (예 R-LEAD_ORG-01)</small>}</label>
      <label className="learning-field">확정 범위 (범위 수정 후 승인 시 사용, 결정적 조건만)<textarea aria-label="확정 범위" className="mono" rows={5} value={scopeText} onChange={(e) => setScopeText(e.target.value)} />{scopeError && <small role="alert">{scopeError}</small>}</label>
      <div className="learning-actions">
        {row('approve', '승인', () => handlers.approve(ruleId, reason.trim(), undefined, acknowledgeInsufficient), hasReason && (!requiresInsufficientAck || (acknowledgeInsufficient && sufficientReason)) && ruleIdOk, !hasReason ? needReason : !ruleIdOk ? '규칙 ID 형식을 확인해 주세요.' : '자료 부족 확인 체크와 10자 이상 사유가 필요합니다.', 'primary')}
        {row('approve_scope', '범위 수정 후 승인', approveWithScope, hasReason && (!requiresInsufficientAck || (acknowledgeInsufficient && sufficientReason)) && ruleIdOk, !hasReason ? needReason : !ruleIdOk ? '규칙 ID 형식을 확인해 주세요.' : '자료 부족 확인 체크와 10자 이상 사유가 필요합니다.')}
        {row('reject', '기각', () => handlers.reject(reason.trim()), hasReason, needReason)}
      </div>
    </>}
    {retryDecision && <p className="learning-caution" role="status">승인(결정 {retryDecision})은 저장됐지만 규칙 버전 생성에 실패했습니다. 규칙 ID를 확인하고 다시 시도하세요.</p>}
    {showVersion && <>
      <fieldset className="learning-range"><legend>검증 조건 (저장된 판단을 기준·후보 규칙으로 재평가)</legend>
        <label>시작<input type="datetime-local" aria-label="검증 시작" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
        <label>끝<input type="datetime-local" aria-label="검증 끝" value={to} onChange={(e) => setTo(e.target.value)} /></label>
        <label>호출 상한(컨텍스트 규칙만)<input inputMode="numeric" aria-label="호출 상한" value={maxCalls} onChange={(e) => setMaxCalls(e.target.value.replace(/\D/g, ''))} /></label>
      </fieldset>
      <div className="learning-actions">
        {row('validate', '검증 실행', () => handlers.validate({ from: new Date(from).toISOString(), to: new Date(to).toISOString(), ...(maxCalls ? { max_calls: Number(maxCalls) } : {}) }))}
        {row('mark_validated', '검증 완료 처리', () => handlers.markValidated(reason.trim()), hasReason, needReason)}
        {row('publish', '게시', () => handlers.publish(reason.trim()), hasReason, needReason, 'primary')}
        {row('stop', '중단', () => handlers.stop(reason.trim()), hasReason, needReason)}
        <div className="learning-action">
          <label className="learning-inline">되돌리기 대상 버전
            <select aria-label="되돌리기 대상 버전" value={target} onChange={(e) => setTarget(e.target.value ? Number(e.target.value) : '')} disabled={!revertTargets.length}>
              {revertTargets.map((v) => <option key={v} value={v}>v{v}</option>)}</select></label>
          <button type="button" className="ui-button secondary" disabled={busy || !states.revert.enabled || !hasReason || target === ''} title={states.revert.reason || undefined} onClick={() => target !== '' && handlers.revert(target, reason.trim())}>되돌리기</button>
          {(states.revert.reason || (!hasReason && needReason)) && <small role="note">비활성: {states.revert.reason || needReason}</small>}
        </div>
      </div>
    </>}
  </section>;
}
