import { StatusBadge } from '../../components';
import { useSlideIndicator } from '../../lib/motion';

export type Progress = { total: number; confirmed: number; deferred: number; remaining: number; percent: number };
export type Split = 'tuning' | 'final';
const SPLITS: [Split, string][] = [['tuning', '튜닝'], ['final', '최종']];

type Props = { split: Split; onSplit: (split: Split) => void; progress: Progress; position: number; total: number; onPrev: () => void; onNext: () => void };

/** Split switch, progress and sample stepper: always visible above the two-column body. */
export function EvalHeader({ split, onSplit, progress, position, total, onPrev, onNext }: Props) {
  const segRef = useSlideIndicator<HTMLDivElement>([split]);
  const share = (n: number) => progress.total ? `${Math.min(100, (n * 100) / progress.total)}%` : '0%';
  return <div className="eval-top">
    <div className="eval-top-row">
      <div ref={segRef} className="eval-seg m-seg" role="tablist" aria-label="분할 선택">
        {SPLITS.map(([id, label]) => <button key={id} type="button" role="tab" aria-selected={split === id} className={split === id ? 'active' : ''} onClick={() => onSplit(id)}>{label}</button>)}
      </div>
      {split === 'final' && <StatusBadge status="review" label="모델 예측 숨김" />}
      <div className="eval-stepper" role="group" aria-label="표본 이동">
        <button type="button" className="eval-step" aria-label="이전 표본" disabled={position <= 1} onClick={onPrev}>‹</button>
        <span className="eval-position" aria-live="polite"><strong>{total ? position : 0}</strong> / {total}</span>
        <button type="button" className="eval-step" aria-label="다음 표본" disabled={position >= total} onClick={onNext}>›</button>
      </div>
    </div>
    <div className="eval-progress" aria-label="진행률">
      <div className="eval-progress-figures">
        <span className="eval-fig done"><b>{progress.confirmed}</b> 확정</span>
        <span className="eval-fig held"><b>{progress.deferred}</b> 보류</span>
        <span className="eval-fig left"><b>{progress.remaining}</b> 남음</span>
        <span className="eval-fig pct">{progress.percent}% 완료</span>
      </div>
      <div className="eval-bar" role="progressbar" aria-label="확정 진행률" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress.percent}>
        <i className="done" style={{ width: share(progress.confirmed) }} /><i className="held" style={{ width: share(progress.deferred) }} />
      </div>
    </div>
  </div>;
}
