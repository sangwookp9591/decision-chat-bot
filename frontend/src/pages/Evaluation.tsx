import { useCallback, useEffect, useRef, useState } from 'react';
import { apiFetch, type ApiError } from '../api/client';
import { EmptyState, ErrorState, Toast } from '../components';
import { useDelayedFlag } from '../state/useDelayedFlag';
import { EvalHeader, type Progress, type Split } from './evaluation/EvalHeader';
import { LabelEditor, type SavePayload } from './evaluation/LabelEditor';
import type { Draft } from './evaluation/options';
import { SampleCard, type Candidate } from './evaluation/SampleCard';
import './evaluation/evaluation.css';

type LoadState = 'loading' | 'ready' | 'forbidden' | 'error';
const noProgress: Progress = { total: 0, confirmed: 0, deferred: 0, remaining: 0, percent: 100 };
const errorMessage = (error: unknown) => (error as Partial<ApiError>)?.message || '저장하지 못했습니다. 잠시 후 다시 시도해 주세요.';

/** Same two-column footprint as the loaded screen so the swap does not move anything. */
function EvalSkeleton() {
  return <div className="eval-body eval-skeleton" role="status" aria-busy="true" aria-label="표본을 불러오는 중">
    <div className="eval-card"><i className="sk w40" /><i className="sk" /><i className="sk" /><i className="sk w60" /><i className="sk h60" /></div>
    <div className="eval-card"><i className="sk w40" /><i className="sk h60" /><i className="sk h60" /><i className="sk h60" /><i className="sk w60" /></div>
  </div>;
}

export function Evaluation() {
  const [split, setSplit] = useState<Split>('tuning');
  const [rows, setRows] = useState<Candidate[]>([]);
  const [progress, setProgress] = useState<Progress>(noProgress);
  const [index, setIndex] = useState(0);
  const [state, setState] = useState<LoadState>('loading');
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; error?: boolean }>({ message: '' });
  const latest = useRef(0);
  const showSkeleton = useDelayedFlag(state === 'loading');

  const load = useCallback(async (keepIndex = false) => {
    const ticket = ++latest.current;
    if (!keepIndex) setState('loading');
    try {
      const data = await apiFetch<{ candidates: Candidate[]; progress: Progress }>(`/api/evaluation/candidates?split=${split}`);
      if (ticket !== latest.current) return;
      setRows(data.candidates); setProgress(data.progress); setState('ready');
      setIndex((n) => keepIndex ? Math.min(n, Math.max(data.candidates.length - 1, 0)) : 0);
    } catch (error) {
      if (ticket !== latest.current) return;
      if (!keepIndex) { setRows([]); setProgress(noProgress); }
      setState((error as Partial<ApiError>)?.status === 403 ? 'forbidden' : keepIndex ? 'ready' : 'error');
      if (keepIndex) setToast({ message: errorMessage(error), error: true });
    }
  }, [split]);
  useEffect(() => { void load(); }, [load]);

  const row = rows[index];
  const submit = async (path: string, init: RequestInit, done: string) => {
    setSaving(true);
    try { await apiFetch(path, init); setToast({ message: done }); await load(true); }
    catch (error) { setToast({ message: errorMessage(error), error: true }); }
    finally { setSaving(false); }
  };
  const save = (payload: SavePayload) => row && submit(`/api/evaluation/candidates/${split}/${row.id}`, { method: 'PUT', body: JSON.stringify(payload) }, payload.status === 'deferred' ? '보류 사유를 기록했습니다.' : '라벨을 확정했습니다.');
  const consensus = (labels: Draft, confidence: number) => row && submit(`/api/evaluation/candidates/${split}/${row.id}/consensus`, { method: 'POST', body: JSON.stringify({ labels, confidence }) }, '합의 라벨을 확정했습니다.');
  const prev = useCallback(() => setIndex((n) => Math.max(n - 1, 0)), []);
  const next = useCallback(() => setIndex((n) => Math.min(n + 1, Math.max(rows.length - 1, 0))), [rows.length]);

  return <section className="eval-page">
    <p className="eyebrow">정답 라벨</p><h1>평가 정답 확정</h1>
    <EvalHeader split={split} onSplit={(value) => { if (value !== split) { setSplit(value); setState('loading'); } }} progress={progress} position={index + 1} total={rows.length} onPrev={prev} onNext={next} />
    {state === 'loading' && (showSkeleton ? <EvalSkeleton /> : <div className="eval-body-reserve" aria-hidden="true" />)}
    {state === 'forbidden' && <EmptyState title="평가 라벨 권한이 없습니다">평가 정답은 라벨러 또는 검토자 역할만 입력할 수 있습니다. 필요하면 관리자에게 역할을 요청하세요.</EmptyState>}
    {state === 'error' && <ErrorState title="표본을 불러오지 못했습니다" onRetry={() => void load()}>네트워크 상태를 확인한 뒤 다시 시도해 주세요.</ErrorState>}
    {state === 'ready' && !row && <EmptyState title="표본이 없습니다">{split === 'final' ? '최종' : '튜닝'} 분할에 확정할 표본이 없습니다.</EmptyState>}
    {state === 'ready' && row && <div className="eval-body">
      <SampleCard row={row} userId={row.my_labels?.user_id} />
      <LabelEditor key={row.id} row={row} saving={saving} hasPrev={index > 0} hasNext={index < rows.length - 1} onSave={(payload) => void save(payload)} onConsensus={(labels, confidence) => void consensus(labels, confidence)} onPrev={prev} onNext={next} />
    </div>}
    <Toast message={toast.message} kind={toast.error ? 'error' : undefined} onClose={() => setToast({ message: '' })} />
  </section>;
}
