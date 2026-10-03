import { useEffect, useState } from 'react';
import { learningApi, type CorrectionCase } from '../../api/learning';
import { fieldLabel, formatTime, valueText } from '../learning/learningModel';
import '../learning/learning.css';

/** Review 상세의 '규칙 학습 연결': 저장된 Correction의 AI 원안·수정 비교와 규칙 학습 이동 안내. */
export function RuleLearningLink({ requestId, refreshKey = '' }: { requestId: string; refreshKey?: string }) {
  const [rows, setRows] = useState<CorrectionCase[] | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let live = true;
    setRows(null); setError('');
    learningApi.requestCorrections(requestId).then((r) => { if (live) setRows(r.corrections); }, (e) => { if (live) setError((e as { message?: string }).message || '수정 기록을 불러오지 못했습니다.'); });
    return () => { live = false; };
  }, [requestId, refreshKey]);
  return <section className="learning-card review-learning-link" aria-label="규칙 학습 연결">
    <h3>규칙 학습 연결</h3>
    <p className="learning-hint">이 요청의 수정 승인은 이 요청에만 적용됩니다. 요청 한 건의 수정 승인은 규칙 게시가 아닙니다. 공통 규칙은 규칙 학습에서 규칙 관리자가 별도로 검토합니다.</p>
    {error && <p role="alert" className="learning-error">{error}</p>}
    {rows && rows.length === 0 && <p className="learning-empty">저장된 수정 기록이 없습니다. 원안 그대로 승인된 요청은 비교할 수정이 없습니다.</p>}
    {rows && rows.length > 0 && <div className="table-scroll" tabIndex={0} aria-label="표, 좌우 화살표 키로 이동"><table>
      <caption className="sr-only">AI 원안과 수정 비교</caption>
      <thead><tr><th scope="col">항목</th><th scope="col">AI 원안</th><th scope="col">수정</th><th scope="col">수정자 · 시각</th><th scope="col">입력 · 실행 · Config</th></tr></thead>
      <tbody>{rows.map((c) => <tr key={c.id}><td>{fieldLabel(c.field)}</td><td>{valueText(c.ai_value)}</td><td>{valueText(c.corrected_value)}</td><td>{c.corrected_by || '—'} · {formatTime(c.corrected_at)}</td><td className="mono">{c.revision_id || '—'} · {c.run_id || '—'} · v{c.config_version ?? '—'}</td></tr>)}</tbody></table></div>}
    <p><a href="/learning">규칙 학습 열기</a> · <a href={`/judgment-map?request_id=${encodeURIComponent(requestId)}`}>판단 맵에서 경로 보기</a></p>
  </section>;
}
