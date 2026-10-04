import { StatusBadge, type StatusKind } from '../../components';
import { RawDetails } from '../../components/RawDetails';
import { consensusLabel, decisionStatusLabel as baseStatusLabel, evaluationFieldLabel } from '../../lib/labels';
import { formatTime } from '../../lib/format';
import { LABEL_FIELDS } from './options';

export type Decision = { labels: Record<string, unknown>; status: string; reason?: string; user_id?: string; created_at?: string };
export type Candidate = { id: string; text: string; rationale?: string; proposed_labels?: Record<string, unknown>; my_labels?: Decision & { confidence?: number }; labels: Decision[]; consensus: string };

const consensusBadge: Record<string, { status: StatusKind; label: string }> = {
  agreed: { status: 'success', label: '일치' },
  resolved: { status: 'success', label: '합의 완료' },
  consensus_required: { status: 'failure', label: '불일치 · 합의 필요' },
  single_label: { status: 'pending', label: '1명 라벨' },
  unlabeled: { status: 'pending', label: '라벨 없음' },
};
const decisionBadge: Record<string, StatusKind> = { confirmed: 'success', deferred: 'review', consensus_confirmed: 'success' };
const decisionStatusLabel = (status: string) => status === 'consensus_confirmed' ? '합의 확정' : baseStatusLabel(status);
const asList = (value: unknown): string[] => Array.isArray(value) ? value.map(String) : value == null || value === '' ? [] : [String(value)];

/** Label values as readable chips, one row per field: nothing is shown as JSON text. */
export function LabelChips({ labels }: { labels: Record<string, unknown> }) {
  return <dl className="eval-chip-summary">{LABEL_FIELDS.filter((field) => field.key in labels).map((field) => {
    const items = asList(labels[field.key]);
    return <div key={field.key}><dt>{evaluationFieldLabel(field.key)}</dt><dd>{items.length ? items.map((item) => <span key={item} className="eval-tag">{item}</span>) : <span className="eval-tag none">{field.kind === 'multi' ? '없음' : '—'}</span>}</dd></div>;
  })}</dl>;
}

export function SampleCard({ row, userId }: { row: Candidate; userId?: string }) {
  const badge = consensusBadge[row.consensus] || { status: 'review' as StatusKind, label: '확인 필요' };
  const mine = row.my_labels;
  return <section className="eval-card eval-sample" aria-labelledby="eval-sample-title">
    <header className="eval-card-head"><h2 id="eval-sample-title">표본 <span className="mono">{row.id}</span></h2>
      {mine && <StatusBadge status={decisionBadge[mine.status] || 'pending'} label={`내 결정 · ${decisionStatusLabel(mine.status)}`} />}</header>
    <p className="eval-request-text">{row.text}</p>
    {row.proposed_labels && <div className="eval-block"><h3>제안 라벨</h3><LabelChips labels={row.proposed_labels} /><RawDetails label="기술 상세">{row.proposed_labels}</RawDetails></div>}
    {row.rationale && <div className="eval-block"><h3>근거 메모</h3><p className="eval-rationale">{row.rationale}</p></div>}
    <div className="eval-block"><h3>합의 상태</h3>
      <p className="eval-consensus"><StatusBadge status={badge.status} label={badge.label} /><span>{consensusLabel(row.consensus)}</span></p>
      <RawDetails label="기술 상세">{row.consensus}</RawDetails></div>
    <div className="eval-block"><h3>다른 라벨러 이력 <span className="eval-count">{row.labels.length}건</span></h3>
      {row.labels.length === 0 ? <p className="eval-muted">아직 기록된 라벨이 없습니다.</p> : <ul className="eval-history">{row.labels.map((decision, i) => <li key={`${decision.user_id}-${i}`}>
        <div className="eval-history-head"><strong>{decision.user_id}{decision.user_id && decision.user_id === userId ? ' (나)' : ''}</strong>
          <StatusBadge status={decisionBadge[decision.status] || 'pending'} label={decisionStatusLabel(decision.status)} />
          <time dateTime={decision.created_at}>{formatTime(decision.created_at, { dateStyle: 'short', timeStyle: 'short' })}</time></div>
        <LabelChips labels={decision.labels} />
        {decision.reason && <p className="eval-reason">보류 사유: {decision.reason}</p>}</li>)}</ul>}
    </div>
  </section>;
}
