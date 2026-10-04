import { StatusBadge } from '../../components';
import { useDelayedFlag, useSlowNotice } from '../../state/useDelayedFlag';
import type { ProgressState } from '../../state/progress';

export const classificationLabels: Record<string, string> = { ai_need: 'AI 필요성', feasibility: '개발 가능성', urgency: '긴급도', lead_org: '주관 조직' };
export const classificationChoices: Record<string, string[]> = { ai_need: ['필요', '불필요', '혼합'], feasibility: ['가능', '조건부 가능', '현재 불가'], urgency: ['긴급', '일반'], lead_org: ['AI팀', 'IT팀', '현업'] };
export const PROVISIONAL_NOTE = '잠정 — 근거와 업무 분해를 확인하는 중';
const stepLabels: Record<string, string> = { '입력 정리': '내용 정리', '업무 분해': '업무 나누기' };
export const stepLabel = (name: string) => stepLabels[name] || name;
export const isWorking = (phase: ProgressState['phase']) => phase === 'submitting' || phase === 'received' || phase === 'preliminary';

/** Gray blocks shaped like the final content; withheld for the first 200ms so quick loads never flash. */
export function Skeleton({ rows = 2, label }: { rows?: number; label: string }) {
  const visible = useDelayedFlag(true, 200);
  return <div className="skeleton-area" role="status" aria-busy="true" aria-label={label}>{visible && Array.from({ length: rows }, (_, index) => <span key={index} className="skeleton" aria-hidden="true" />)}</div>;
}

/** Shown while the run is still working; tells the user it is not stuck once it passes 5 seconds. */
export function SlowNotice({ state }: { state: ProgressState }) {
  const slow = useSlowNotice(isWorking(state.phase), 5000);
  if (!slow) return null;
  return <p className="slow-notice" role="status">조금 더 걸리고 있어요{state.currentStep ? ` · 현재 단계: ${stepLabel(state.currentStep)}` : ''}. 결과가 준비되는 대로 바로 보여 드릴게요.</p>;
}

/** Same set the final `Result` treats as an uncertain classification, so its guidance can occupy its slot from the provisional stage. */
export const UNCERTAIN_VALUES = ['정보 부족', '판단 보류', '미정'];
export const OPEN_LATER = '원문 열람은 최종 저장 후 가능';
/**
 * Cards from judgment.partial / judgment_saved payloads, shown until the saved judgment is loaded.
 * Same areas in the same order and slots as `Result` (summary → judgment → tasks), so the final swap only replaces data:
 * "N items prepared" is one line, "details can be opened" is a separate, explicit state.
 */
export function ProvisionalResult({ state }: { state: ProgressState }) {
  const final = state.phase === 'final';
  const values = final ? state.finalClassifications ?? state.preliminary?.classifications : state.preliminary?.classifications;
  if (!values || !Object.keys(values).length) return null;
  const keys = Object.keys(classificationLabels).filter((key) => key in values);
  return <div className="result-stack provisional-result" aria-busy={!final}>
    <article className="result-summary" data-region="summary"><div className="card-heading"><h2>판단 결과</h2>{final ? <StatusBadge status="progress" label="저장 확인 중" /> : <StatusBadge status="progress" label="잠정 판단" />}</div>
      <div className="summary-text"><Skeleton rows={2} label="요약을 정리하는 중" /></div>
      <p className="author-line provisional-note" role="status">{final ? '최종 판단을 저장했어요. 결과를 불러오는 중' : PROVISIONAL_NOTE}</p>
      <code className="provisional-count">{state.evidenceReady ? (state.evidenceCount !== undefined ? `근거 ${state.evidenceCount}건 연결됨` : '근거 연결됨') : '\u00a0'}</code></article>
    <div className="judgment-grid" data-region="judgment">{keys.map((key) => { const value = String(values[key]); const selected = value === '조건부' ? '조건부 가능' : value; const confidence = state.preliminary?.confidences[key]; const uncertain = UNCERTAIN_VALUES.includes(value);
      return <article className="judgment-card" key={key}><h3>{classificationLabels[key]}{!final && <span className="provisional-badge">잠정</span>}</h3><div className="scale-options">{(classificationChoices[key] || [value]).map((choice) => <span key={choice} className={!uncertain && selected === choice ? 'selected' : ''}>{choice}</span>)}</div>{uncertain && <div className="uncertain-result"><strong>정보 부족·판단 보류</strong><span>{value}</span></div>}<div className="signal-labels">{typeof confidence === 'number' && <span>선택 신뢰도 {(confidence * 100).toFixed(0)}%</span>}</div>
        <div className="evidence-list">{state.evidenceReady ? <span>{OPEN_LATER}</span> : <Skeleton rows={2} label="근거를 연결하는 중" />}</div></article>; })}</div>
    <article className="result-summary" data-region="tasks"><h2>업무 분담</h2>{state.tasksReady ? <p>{state.taskCount !== undefined ? `업무 ${state.taskCount}건 준비됨` : '업무 분해 준비됨'}</p> : <Skeleton rows={3} label="업무를 나누는 중" />}
      {!final && <button type="button" className="ui-button secondary" disabled aria-disabled="true">검토·배정은 최종 판단 저장 후 가능해요</button>}</article>
  </div>;
}
