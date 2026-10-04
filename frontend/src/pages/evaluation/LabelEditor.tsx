import { useEffect, useId, useRef, useState } from 'react';
import { Button } from '../../components';
import { ChipGroup } from './ChipGroup';
import { LABEL_FIELDS, SHORTCUT_FIELDS, draftFrom, missingSingleFields, type Draft } from './options';
import type { Candidate } from './SampleCard';
import { evaluationFieldLabel } from '../../lib/labels';

export type SavePayload = { labels: Draft; confidence: number; status: 'confirmed' | 'deferred'; reason: string | null };
type Props = { row: Candidate; saving: boolean; hasPrev: boolean; hasNext: boolean; onSave: (payload: SavePayload) => void; onConsensus: (labels: Draft, confidence: number) => void; onPrev: () => void; onNext: () => void };

const TICKS = [0, 25, 50, 75, 100];

/** The answer form and its action bar. Mounted per sample (keyed by id) so each sample starts from its own saved or proposed answer. */
export function LabelEditor({ row, saving, hasPrev, hasNext, onSave, onConsensus, onPrev, onNext }: Props) {
  const [draft, setDraft] = useState<Draft>(() => draftFrom(row.my_labels?.labels ?? row.proposed_labels));
  const [confidence, setConfidence] = useState(row.my_labels?.confidence ?? 0.8);
  const [reason, setReason] = useState(row.my_labels?.status === 'deferred' ? row.my_labels.reason || '' : '');
  const [reasonError, setReasonError] = useState(false);
  const reasonRef = useRef<HTMLTextAreaElement>(null);
  const reasonId = useId();
  const reasonHintId = useId();
  const missing = missingSingleFields(draft);

  const confirm = () => { if (!saving && !missing.length) onSave({ labels: draft, confidence, status: 'confirmed', reason: null }); };
  const defer = () => {
    if (saving) return;
    if (!reason.trim()) { setReasonError(true); reasonRef.current?.focus(); return; }
    onSave({ labels: draft, confidence, status: 'deferred', reason: reason.trim() });
  };
  const live = useRef({ confirm, onPrev, onNext });
  useEffect(() => { live.current = { confirm, onPrev, onNext }; });
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      const target = event.target instanceof Element ? event.target : null;
      if (target?.closest('textarea, input[type="text"], select')) return;
      const key = event.key.toLowerCase();
      if (key === 'j') { event.preventDefault(); live.current.onNext(); }
      else if (key === 'k') { event.preventDefault(); live.current.onPrev(); }
      else if (event.key === 'Enter') {
        // A focused button, link or summary keeps its own Enter behavior; radio chips and the page itself confirm.
        if (target?.closest('button, a, summary') && !target.closest('[role="radio"]')) return;
        event.preventDefault(); live.current.confirm();
      } else if (/^[1-4]$/.test(event.key)) {
        const group = document.getElementById(`eval-group-${SHORTCUT_FIELDS[Number(event.key) - 1]}`);
        (group?.querySelector<HTMLElement>('[data-chip][tabindex="0"]') ?? group?.querySelector<HTMLElement>('[data-chip]'))?.focus();
      }
    };
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey);
  }, []);

  return <section className="eval-card eval-editor" aria-labelledby="eval-editor-title">
    <header className="eval-card-head"><h2 id="eval-editor-title">정답 입력</h2><span className="eval-muted">숫자 1–4로 항목 이동</span></header>
    {LABEL_FIELDS.map((field, i) => <ChipGroup key={field.key} field={field} shortcut={i < 4 ? i + 1 : undefined} value={draft[field.key]} disabled={saving}
      onChange={(value) => setDraft((current) => ({ ...current, [field.key]: value }))} />)}
    <div className="eval-field">
      <div className="eval-field-head"><label htmlFor="eval-confidence">확신도</label><span className="eval-confidence-value" aria-hidden="true">{Math.round(confidence * 100)}%</span></div>
      <input id="eval-confidence" className="eval-range" type="range" min="0" max="1" step="0.05" value={confidence} disabled={saving} onChange={(e) => setConfidence(Number(e.target.value))} aria-valuetext={`${Math.round(confidence * 100)}%`} list="eval-ticks" />
      <datalist id="eval-ticks">{TICKS.map((t) => <option key={t} value={t / 100} />)}</datalist>
      <div className="eval-ticks" aria-hidden="true">{TICKS.map((t) => <span key={t}>{t}</span>)}</div>
    </div>
    <div className="eval-field">
      <label className="eval-field-head" htmlFor={reasonId}><span>보류 사유</span></label>
      <p id={reasonHintId} className="eval-field-hint">판단을 보류할 때만 필수입니다. 확정할 때는 비워 둡니다.</p>
      <textarea id={reasonId} ref={reasonRef} className="eval-textarea" rows={2} value={reason} disabled={saving} aria-invalid={reasonError || undefined}
        aria-describedby={reasonError ? `${reasonHintId} ${reasonId}-error` : reasonHintId} onChange={(e) => { setReason(e.target.value); if (e.target.value.trim()) setReasonError(false); }} />
      {reasonError && <p id={`${reasonId}-error`} className="eval-error-text" role="alert">보류 사유를 입력해 주세요.</p>}
    </div>
    <div className="eval-actions" role="group" aria-label="저장 동작">
      <p className="eval-actions-note" aria-live="polite">{saving ? '저장 중…' : missing.length ? `${missing.map((f) => evaluationFieldLabel(f.key)).join('·')}을(를) 선택하면 확정할 수 있습니다.` : ' '}</p>
      <div className="eval-actions-row">
        <Button variant="primary" className="eval-confirm" aria-label="확정 (Enter)" aria-keyshortcuts="Enter" disabled={saving || missing.length > 0} onClick={confirm}>확정 <kbd>Enter</kbd></Button>
        <Button variant="plain" disabled={saving} onClick={defer}>보류</Button>
        {row.consensus === 'consensus_required' && <Button variant="secondary" disabled={saving || missing.length > 0} onClick={() => onConsensus(draft, confidence)}>합의 라벨 확정</Button>}
        <span className="eval-actions-spacer" />
        <Button variant="plain" aria-label="이전 (K)" aria-keyshortcuts="K" disabled={!hasPrev} onClick={onPrev}>이전 <kbd>K</kbd></Button>
        <Button variant="plain" aria-label="다음 (J)" aria-keyshortcuts="J" disabled={!hasNext} onClick={onNext}>다음 <kbd>J</kbd></Button>
      </div>
    </div>
  </section>;
}
