import { useEffect, useState } from 'react';
import { learningApi, type CorrectionCase, type HumanProposal } from '../../api/learning';
import { fieldLabel, valueText } from './learningModel';

const values: Record<string, string[]> = {
  ai_need: ['필요', '불필요', '혼합', '정보 부족'],
  feasibility: ['조건부 가능', '현재 불가', '정보 부족'],
  urgency: ['긴급'], lead_org: ['AI팀', 'IT팀', '현업'],
};
export function Proposal({ busy, onSubmit, onClose }: { busy: boolean; onSubmit: (body: HumanProposal) => void; onClose: () => void }) {
  const [field, setField] = useState('ai_need');
  const [value, setValue] = useState(values.ai_need[0]);
  const [scope, setScope] = useState('{"all": []}');
  const [reason, setReason] = useState('');
  const [cases, setCases] = useState<CorrectionCase[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    setLoading(true); setCases([]); setSelected([]); setError('');
    learningApi.corrections({ field }).then((r) => {
      if (live) setCases(r.corrections.filter((c) => c.corrected_value !== undefined));
    }, () => { if (live) setError('지지 수정 기록을 불러오지 못했습니다. 항목을 다시 선택해 주세요.'); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [field]);
  function submit(event: React.FormEvent) {
    event.preventDefault();
    try {
      const parsed = JSON.parse(scope);
      if (!parsed || !Array.isArray(parsed.all)) throw new Error('scope');
      setError('');
      onSubmit({ field, proposed_action: { set: value }, scope: parsed, rationale: reason.trim(), supporting_correction_ids: selected });
    } catch { setError('제안 범위는 {"all": [조건...]} 형식의 JSON이어야 합니다.'); }
  }
  return <form className="learning-card" aria-label="사람 후보 제안" onSubmit={submit}>
    <h2>사람 후보 제안</h2>
    <p>지지 수정 기록과 적용 범위·사유를 선택합니다. 제안은 승인·검증·게시 전까지 실행에 쓰이지 않습니다.</p>
    <p className="learning-note">AI 필요성·실현 가능성·긴급도·담당 조직의 지원 값만 제안할 수 있습니다. 가능으로 상향·긴급 해제·협업 조직·검토 경로·컨텍스트는 이 양식에서 지원하지 않습니다. 서버가 안전 조건과 범위를 확인합니다.</p>
    <label className="learning-field">판단 항목<select aria-label="제안 판단 항목" value={field} onChange={(e) => { setField(e.target.value); setValue(values[e.target.value][0]); }}>{Object.keys(values).map((key) => <option key={key} value={key}>{fieldLabel(key)}</option>)}</select></label>
    <label className="learning-field">제안 값<select aria-label="제안 값" value={value} onChange={(e) => setValue(e.target.value)}>{values[field].map((v) => <option key={v}>{v}</option>)}</select></label>
    <fieldset><legend>지지 Correction 선택</legend>
      {loading ? <p>수정 기록 불러오는 중</p> : cases.length ? cases.map((c) => <label className="learning-field" key={c.id}><span><input type="checkbox" aria-label={`지지 ${c.id}`} checked={selected.includes(c.id)} onChange={(e) => setSelected((ids) => e.target.checked ? [...ids, c.id] : ids.filter((id) => id !== c.id))} /> {c.id} · {c.request_id} · {valueText(c.ai_value)} → {valueText(c.corrected_value)}</span></label>) : <p>이 항목에서 조회 가능한 수정 기록이 없습니다.</p>}
      <p>지지 {selected.length}건 · 3건 미만이면 자료 부족 후보로 저장됩니다.</p>
    </fieldset>
    <label className="learning-field">제안 범위<textarea aria-label="제안 범위" rows={4} value={scope} onChange={(e) => setScope(e.target.value)} /><small>예: {`{"all": [{"requester_org": "IT팀"}]}`} · 빈 조건은 모든 요청</small></label>
    <label className="learning-field">제안 사유<textarea aria-label="제안 사유" maxLength={3000} required value={reason} onChange={(e) => setReason(e.target.value)} /></label>
    {error && <p role="alert">{error}</p>}
    <button type="submit" className="ui-button primary" disabled={busy || loading || !reason.trim()}>후보 제안 저장</button>
    <button type="button" className="ui-button secondary" onClick={onClose} disabled={busy}>닫기</button>
  </form>;
}
