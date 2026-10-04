import { Button, StatusBadge, type StatusKind } from '../../components';
import type { Judgment, requestApi } from '../../api/requests';
import { RawDetails } from '../../components/RawDetails';
import { ShortId } from '../../components/ShortId';
import { locationLabel, reviewReasonLabel } from '../../lib/labels';
import { DraftVersionCompare, sourceLabel } from './DraftVersions';
import { classificationChoices as classifications, classificationLabels as labels, UNCERTAIN_VALUES } from './ProgressivePanel';

type Onevidence = (output: Judgment['outputs'][number], evidence?: Judgment['outputs'][number]['evidence'][number]) => void;
export const BRIEF_KEYS = Object.keys(labels);

/** "업무 3건 · IT팀 2 · AI팀 1": how many tasks and who leads them, in one line. */
export function taskSplit(tasks: Array<Record<string, unknown>>): string {
  if (!tasks.length) return '분해된 업무가 없어요';
  const counts = new Map<string, number>();
  tasks.forEach((task) => { const org = String(task.lead_org || '미정'); counts.set(org, (counts.get(org) || 0) + 1); });
  const parts = [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([org, count]) => `${org} ${count}`);
  return `업무 ${tasks.length}건 · ${parts.slice(0, 3).join(' · ')}${parts.length > 3 ? ` 외 ${parts.length - 3}` : ''}`;
}

/** Plain-text version of the answer for the copy button. */
export function answerText(judgment: Judgment): string {
  const summary = typeof judgment.summary === 'string' ? JSON.parse(judgment.summary) : judgment.summary;
  const lines = BRIEF_KEYS.filter((key) => key in judgment.classifications).map((key) => `${labels[key]}: ${String(judgment.classifications[key])}`);
  return [summary.text || '', ...lines, taskSplit(judgment.draft_tasks)].filter(Boolean).join('\n');
}

/**
 * The result as it appears in the conversation: summary, the four core classifications, a task split line and "자세히 보기".
 * Same regions, slots and heights as the provisional card (ProvisionalResult), so the final swap only replaces data.
 * Everything else (scales, all evidence, task rows, run comparison) is in `Result`, shown in the detail drawer.
 */
export function ResultBrief({ judgment, state, onEvidence, onDetail }: { judgment: Judgment; state?: { status: StatusKind; label: string }; onEvidence: Onevidence; onDetail: () => void }) {
  const summary = typeof judgment.summary === 'string' ? JSON.parse(judgment.summary) : judgment.summary;
  const keys = BRIEF_KEYS.filter((key) => key in judgment.classifications);
  return <div className="result-stack result-brief"><article className="result-summary" data-region="summary"><div className="card-heading"><h2>판단 결과</h2><StatusBadge {...(state ?? { status: judgment.review ? 'review' : 'success', label: judgment.review ? '검토 대기' : '자동 처리 가능' })} /><span className={`environment-badge mode-${judgment.mode}`}>{judgment.mode.toUpperCase()}</span></div>
    <p className="summary-text">{summary.text || '요약 정보가 없습니다.'}</p><p className="author-line">원문 발췌 · 작성 주체: {summary.author || judgment.author || 'Jev'}</p><code>근거 {judgment.outputs.reduce((n, output) => n + output.evidence.length, 0)}건 연결됨</code></article>
    <div className="judgment-grid" data-region="judgment">{keys.map((key) => { const value = String(judgment.classifications[key]); const uncertain = UNCERTAIN_VALUES.includes(value); const related = judgment.outputs.filter((output) => output.question_id.includes(key)); const output = related[0]; const evidence = output?.evidence[0]; const confidence = output?.confidence;
      return <article className="judgment-card" key={key}><h3>{labels[key]}</h3>{uncertain ? <div className="uncertain-result"><strong>정보 부족·판단 보류</strong><span className="judgment-value">{value}</span></div> : <strong className="judgment-value">{value === '조건부' ? '조건부 가능' : value}</strong>}
        <div className="signal-labels">{typeof confidence === 'number' && <span>선택 신뢰도 {(confidence * 100).toFixed(0)}%</span>}</div>
        <div className="evidence-list">{output ? <button type="button" onClick={() => onEvidence(output, evidence)}>{evidence ? '근거 열기' : '근거 패널 열기'}</button> : <span>저장된 근거 위치 없음</span>}</div></article>; })}</div>
    <article className="result-summary" data-region="tasks"><h2>업무 분담</h2><p className="task-split">{taskSplit(judgment.draft_tasks)}</p>
      <div className="brief-actions"><Button type="button" color="primary" tone="weak" onClick={onDetail}>자세히 보기</Button></div></article>
  </div>;
}

export function Result({ judgment, previousJudgment, runs, onEvidence, state }: { judgment: Judgment; state?: { status: StatusKind; label: string }; previousJudgment?: Judgment | null; runs: Awaited<ReturnType<typeof requestApi.runs>> | null; onEvidence: (output: Judgment['outputs'][number], evidence?: Judgment['outputs'][number]['evidence'][number]) => void }) {
  const summary = typeof judgment.summary === 'string' ? JSON.parse(judgment.summary) : judgment.summary;
  const selectedRun = runs?.runs.find((run) => run.id === judgment.run_id); const oldRun = runs?.runs.find((run) => run.id !== judgment.run_id);
  return <div className="result-stack"><article className="result-summary" data-region="summary"><div className="card-heading"><h2>판단 결과</h2><StatusBadge {...(state ?? { status: judgment.review ? 'review' : 'success', label: judgment.review ? '검토 대기' : '자동 처리 가능' })} /><span className={`environment-badge mode-${judgment.mode}`}>{judgment.mode.toUpperCase()}</span></div><p className="summary-text">{summary.text || '요약 정보가 없습니다.'}</p><p className="author-line">원문 발췌 · 작성 주체: {summary.author || judgment.author || 'Jev'}</p><details className="result-ids"><summary>자세히 보기</summary><p>실행 <ShortId id={judgment.run_id}/> · revision <ShortId id={judgment.revision_id}/></p></details></article>
    <div className="judgment-grid" data-region="judgment">{Object.entries(judgment.classifications).map(([key, value]) => { const uncertain = UNCERTAIN_VALUES.includes(String(value)); const selected = String(value) === '조건부' ? '조건부 가능' : String(value); const related = judgment.outputs.filter((output) => output.question_id.includes(key)); return <article className="judgment-card" key={key}><h3>{labels[key] || key}</h3><div className="scale-options">{(classifications[key] || [String(value)]).map((choice) => <span key={choice} className={!uncertain && selected === choice ? 'selected' : ''}>{choice}</span>)}</div>{uncertain && <div className="uncertain-result"><strong>정보 부족·판단 보류</strong><span>{String(value)}</span></div>}<div className="signal-labels">{related.map((output) => <span key={output.id}>{output.confidence !== undefined && `선택 신뢰도 ${(output.confidence * 100).toFixed(0)}%`}{output.noul !== undefined && `Noul 확률 ${JSON.stringify(output.noul)}`}</span>)}</div><div className="evidence-list">{related.length ? related.flatMap((output) => output.evidence.length ? output.evidence.map((evidence) => <button key={evidence.id} type="button" onClick={() => onEvidence(output, evidence)}>{evidence.source === 'chat' ? '채팅' : '첨부'} · {locationLabel(evidence.location)} 근거 열기</button>) : [<button key={`${output.id}-none`} type="button" onClick={() => onEvidence(output)}>저장된 근거 위치 없음 · 근거 패널 열기</button>]) : <span>저장된 근거 위치 없음</span>}</div></article>; })}</div>
    <article className="result-summary" data-region="tasks"><h2>업무 분담{judgment.current_draft_version && (judgment.draft_versions?.length ?? 0) > 1 ? ` (v${judgment.current_draft_version} ${sourceLabel(judgment.draft_versions?.find((v) => v.draft_version === judgment.current_draft_version)?.source)})` : ''}</h2>{judgment.draft_tasks.map((task, index) => <div className="task-row" key={String(task.id || index)}><strong>{String(task.title || '업무 미정')}</strong><span>{String(task.method || '방식 미정')} · 주관 {String(task.lead_org || '미정')}</span><span>협업 {Array.isArray(task.collab_orgs) ? task.collab_orgs.join(', ') || '없음' : '미정'} · 선행 {Array.isArray(task.predecessors) ? task.predecessors.join(', ') || '없음' : '미정'}</span></div>)}<DraftVersionCompare versions={judgment.draft_versions ?? []} currentVersion={judgment.current_draft_version} /><p>검토 사유: {judgment.review_reasons.length ? judgment.review_reasons.map((reason) => reviewReasonLabel(String(reason))).join(' · ') : '추가 검토 사유 없음'}</p>{judgment.review_reasons.length > 0 && <RawDetails>{judgment.review_reasons.map(String).join('\n')}</RawDetails>}</article>
    {oldRun && <article className="result-summary"><h2>이전 실행 비교</h2><p>현재 실행 <ShortId id={String(selectedRun?.id ?? judgment.run_id)} /> · 이전 실행 <ShortId id={oldRun.id} /></p><RawDetails label="버전 정보 자세히">{{ current: selectedRun?.versions || {}, previous: oldRun.versions }}</RawDetails>{previousJudgment ? <ul>{Object.entries(judgment.classifications).map(([key, current]) => <li key={key}>{labels[key] || key}: {String(previousJudgment.classifications[key] ?? '—')} → {String(current)}{String(previousJudgment.classifications[key]) === String(current) ? ' (변경 없음)' : ' (변경)'}</li>)}</ul> : <p>이전 실행의 저장 결과가 없어 버전 정보만 표시합니다.</p>}</article>}
  </div>;
}
