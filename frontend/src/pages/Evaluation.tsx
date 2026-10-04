import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../api/client';
import { consensusLabel, decisionStatusLabel, evaluationFieldInfo, evaluationFieldLabel } from '../lib/labels';

type Decision = { labels: Record<string, unknown>; status: string; reason?: string; user_id?: string };
type Candidate = { id: string; text: string; rationale?: string; proposed_labels?: Record<string, unknown>; my_labels?: Decision; labels: Decision[]; consensus: string };
type Progress = { total: number; confirmed: number; deferred: number; remaining: number; percent: number };
const fields = ['ai_need', 'feasibility', 'urgency', 'team_set', 'risk_areas'];
const show = (value: unknown) => Array.isArray(value) ? (value.length ? value.join(', ') : '없음') : value == null || value === '' ? '—' : String(value);
const labelSummary = (labels: Record<string, unknown>) => fields.filter((key) => key in labels).map((key) => `${evaluationFieldLabel(key)} ${show(labels[key])}`).join(' · ');

export function Evaluation() {
  const [split, setSplit] = useState<'tuning' | 'final'>('tuning');
  const [rows, setRows] = useState<Candidate[]>([]);
  const [progress, setProgress] = useState<Progress>({ total: 0, confirmed: 0, deferred: 0, remaining: 0, percent: 100 });
  const [index, setIndex] = useState(0);
  const [confidence, setConfidence] = useState(0.8);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [deferReason, setDeferReason] = useState('');
  const [notice, setNotice] = useState('');
  const load = useCallback(async (keepIndex = false) => {
    const data = await apiFetch<{ candidates: Candidate[]; progress: Progress }>(`/api/evaluation/candidates?split=${split}`);
    setRows(data.candidates); setProgress(data.progress);
    if (!keepIndex) setIndex(0);
  }, [split]);
  useEffect(() => { void load(); }, [load]);
  const row = rows[index];
  useEffect(() => { setLabels({}); setDeferReason(''); }, [row?.id]);
  const parseLabels = () => Object.fromEntries(fields.map((key) => {
    const value = labels[key] ?? JSON.stringify(row?.my_labels?.labels[key] ?? row?.proposed_labels?.[key] ?? '');
    try { return [key, JSON.parse(value)]; } catch { return [key, value]; }
  }));
  const save = useCallback(async (status: 'confirmed' | 'deferred' = 'confirmed') => {
    if (!row) return;
    await apiFetch(`/api/evaluation/candidates/${split}/${row.id}`, { method: 'PUT', body: JSON.stringify({ labels: parseLabels(), confidence, status, reason: status === 'deferred' ? deferReason : null }) });
    setNotice(status === 'deferred' ? '보류 사유를 기록했습니다.' : '라벨을 확정했습니다.');
    await load(true);
  }, [row, split, labels, confidence, deferReason, load]);
  const resolveConsensus = async () => {
    if (!row) return;
    await apiFetch(`/api/evaluation/candidates/${split}/${row.id}/consensus`, { method: 'POST', body: JSON.stringify({ labels: parseLabels(), confidence }) });
    setNotice('합의 라벨을 확정했습니다.'); await load(true);
  };
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const editing = event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement;
      if (editing && event.key !== 'Enter') return;
      if (event.key.toLowerCase() === 'j') { event.preventDefault(); setIndex((n) => Math.min(n + 1, rows.length - 1)); }
      else if (event.key.toLowerCase() === 'k') { event.preventDefault(); setIndex((n) => Math.max(n - 1, 0)); }
      else if (event.key === 'Enter') { event.preventDefault(); void save(); }
      else if (/^[1-4]$/.test(event.key)) document.getElementById(`label-${fields[Number(event.key) - 1]}`)?.focus();
    };
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey);
  }, [rows.length, save]);
  return <section>
    <p className="eyebrow">EVALUATION LABELS</p><h1>평가 정답 확정</h1>
    <label>분할 <select value={split} onChange={(e) => setSplit(e.target.value as 'tuning' | 'final')}><option value="tuning">튜닝</option><option value="final">최종</option></select></label>
    <p aria-label="진행률">{progress.confirmed} / {progress.total} 확정 · 보류 {progress.deferred} · 남음 {progress.remaining} ({progress.percent}%)</p>
    <progress max={100} value={progress.percent} aria-label="확정 진행률" />
    {row && <article><h2>{row.id}</h2><p>{row.text}</p>{row.proposed_labels && <div>제안 라벨: {labelSummary(row.proposed_labels)}<details><summary>기술 상세</summary><code>{JSON.stringify(row.proposed_labels)}</code></details></div>}{row.rationale && <p>근거 메모: {row.rationale}</p>}<div>합의 상태: {consensusLabel(row.consensus)}<details><summary>기술 상세</summary><code>{row.consensus}</code></details></div>
      {fields.map((key, i) => <label key={key} htmlFor={`label-${key}`}>{i < 4 ? `${i + 1}. ` : ''}{evaluationFieldLabel(key)} <small>{evaluationFieldInfo[key]?.hint}</small> <input id={`label-${key}`} value={labels[key] ?? JSON.stringify(row.my_labels?.labels[key] ?? row.proposed_labels?.[key] ?? '')} onChange={(e) => setLabels((current) => ({ ...current, [key]: e.target.value }))} /></label>)}
      <label>확신도 <input type="range" min="0" max="1" step="0.05" value={confidence} onChange={(e) => setConfidence(Number(e.target.value))} /></label>
      <button onClick={() => void save()}>확정 (Enter)</button>
      <label>보류 사유 <input value={deferReason} onChange={(e) => setDeferReason(e.target.value)} /></label><button disabled={!deferReason.trim()} onClick={() => void save('deferred')}>보류</button>
      {row.consensus === 'consensus_required' && <button onClick={() => void resolveConsensus()}>합의 라벨 확정</button>}
      <button onClick={() => setIndex((n) => Math.min(n + 1, rows.length - 1))}>다음 (J)</button><button onClick={() => setIndex((n) => Math.max(n - 1, 0))}>이전 (K)</button>
      {row.labels.map((decision, i) => <details key={`${decision.user_id}-${i}`}><summary>{decision.user_id} · {decisionStatusLabel(decision.status)}</summary><p>{labelSummary(decision.labels)}</p><pre>{JSON.stringify(decision.labels, null, 2)}</pre>{decision.reason && <p>보류 사유: {decision.reason}</p>}</details>)}
    </article>}{notice && <p role="status">{notice}</p>}
  </section>;
}
