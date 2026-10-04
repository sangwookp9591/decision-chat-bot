import { useEffect, useState } from 'react';
import { apiFetch } from '../api/client';

type Candidate = { id: string; text: string; rationale: string; proposed_labels: Record<string, unknown>; labels: Array<{ labels: string; status: string }>; consensus: string };
export function Evaluation() {
  const [split, setSplit] = useState<'tuning' | 'final'>('tuning');
  const [rows, setRows] = useState<Candidate[]>([]);
  const [index, setIndex] = useState(0);
  const [confidence, setConfidence] = useState(0.8);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState('');
  const load = async () => { const data = await apiFetch<{ candidates: Candidate[] }>(`/api/evaluation/candidates?split=${split}`); setRows(data.candidates); setIndex(0); };
  useEffect(() => { void load(); }, [split]);
  const row = rows[index];
  const save = async () => { if (!row) return; const finalLabels = Object.fromEntries(Object.entries(labels).map(([key, value]) => { try { return [key, JSON.parse(value)]; } catch { return [key, value]; } })); await apiFetch(`/api/evaluation/candidates/${split}/${row.id}`, { method: 'PUT', body: JSON.stringify({ labels: { ...row.proposed_labels, ...finalLabels }, confidence, status: 'confirmed' }) }); setNotice('라벨을 기록했습니다.'); await load(); };
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return; if (event.key === 'j') setIndex((n) => Math.min(n + 1, rows.length - 1)); if (event.key === 'k') setIndex((n) => Math.max(n - 1, 0)); if (event.key === 'Enter') void save(); if (/^[1-4]$/.test(event.key)) document.getElementById(`label-${Object.keys(row?.proposed_labels || {})[Number(event.key) - 1]}`)?.focus(); };
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey);
  }, [rows, index, confidence]);
  return <section><p className="eyebrow">EVALUATION LABELS</p><h1>평가 정답 확정</h1><label>분할 <select value={split} onChange={(e) => setSplit(e.target.value as 'tuning' | 'final')}><option value="tuning">튜닝</option><option value="final">최종</option></select></label><p>{rows.filter((x) => x.labels.some((l) => l.status === 'confirmed')).length} / {rows.length} 확정</p>{row && <article><h2>{row.id}</h2><p>{row.text}</p><p>제안 라벨: {JSON.stringify(row.proposed_labels)}</p><p>근거 메모: {row.rationale}</p><p>합의 상태: {row.consensus}</p>{Object.entries(row.proposed_labels).map(([key, value], i) => <label key={key} htmlFor={`label-${key}`}>{i + 1}. {key} <input id={`label-${key}`} value={labels[key] ?? JSON.stringify(value)} onChange={(e) => setLabels((current) => ({ ...current, [key]: e.target.value }))} /></label>)}<label>확신도 <input type="range" min="0" max="1" step="0.05" value={confidence} onChange={(e) => setConfidence(Number(e.target.value))} /></label><button onClick={() => void save()}>확정 (Enter)</button><button onClick={() => setIndex((n) => Math.min(n + 1, rows.length - 1))}>다음 (J)</button><button onClick={() => setIndex((n) => Math.max(n - 1, 0))}>이전 (K)</button></article>}{notice && <p role="status">{notice}</p>}</section>;
}
