import { applicabilityLabel, caseStatusLabel, type PrecedentEntry } from '../../api/cases';
import { Button } from '../../components';

const text = (value: unknown) => (value == null || value === '' ? '—' : String(value));

/** 과거 검토자의 판단 사례를 참고로만 보여 준다. 값은 검토자가 직접 고를 때만 바뀐다. */
export function Precedents({ label, entry, disabled, onUse }: { label: string; entry?: PrecedentEntry; disabled?: boolean; onUse: (value: string) => void }) {
  if (!entry?.items.length) return null;
  return <div className="review-precedents" aria-label={`${label} 참고 선례`}>
    <strong>{label} · 참고 선례 {entry.items.length}건</strong>
    {entry.conflict && <p role="note" className="review-precedent-conflict">선례끼리 결론이 다릅니다. 조건과 사유를 비교해 판단하세요.</p>}
    {entry.items.map((p) => <blockquote key={p.id} className={`review-precedent is-${p.applicability}`}>
      <p><b>{applicabilityLabel[p.applicability]}{p.matched_keyword ? ` (‘${p.matched_keyword}’)` : ''}</b> · {caseStatusLabel[p.status]}{p.stale ? ' · 오래된 사례' : ''}</p>
      <p>AI 원안 {text(p.ai_value)} → 검토자 판단 <b>{text(p.corrected_value)}</b> · “{p.situation || '제목 없는 요청'}”</p>
      <p>사유: {p.reason}</p>
      {(p.conditions.length > 0 || p.exceptions.length > 0) && <small>적용 조건 {p.conditions.join(', ') || '—'} · 예외 {p.exceptions.join(', ') || '없음'}</small>}
      <small>선례로 참고 {p.consulted}회 · 그대로 따름 {p.followed}회{p.outcome ? ` · 결과 ${p.outcome === 'held' ? '유효' : '실패'}` : ' · 실제 결과 미기록'}</small>
      {p.applicability !== 'excepted' && <Button type="button" variant="plain" className="review-source" disabled={disabled} onClick={() => onUse(text(p.corrected_value))}>이 값으로 채우기</Button>}
    </blockquote>)}
  </div>;
}
