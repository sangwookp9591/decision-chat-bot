import { useEffect, useState } from 'react';
import { learningApi, type CorrectionCase, type HumanProposal, type LearningOrg, type RuleScope } from '../../api/learning';
import { orgLabel } from '../../lib/labels';
import { fieldLabel, valueText } from './learningModel';

const values: Record<string, string[]> = {
  ai_need: ['필요', '불필요', '혼합', '정보 부족'],
  feasibility: ['조건부 가능', '현재 불가', '정보 부족'],
  urgency: ['긴급'], lead_org: ['AI팀', 'IT팀', '현업'],
};
export function Proposal({ busy, onSubmit, onClose }: { busy: boolean; onSubmit: (body: HumanProposal) => void; onClose: () => void }) {
  const [field, setField] = useState('ai_need');
  const [value, setValue] = useState(values.ai_need[0]);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keyword, setKeyword] = useState('');
  const [orgs, setOrgs] = useState<LearningOrg[]>([]);
  const [org, setOrg] = useState('');
  const [conditionField, setConditionField] = useState('');
  const [conditionValue, setConditionValue] = useState('');
  const [direct, setDirect] = useState(false);
  const [orgError, setOrgError] = useState('');
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
  const formScope: RuleScope = { all: [
    ...(keywords.length ? [{ text: { contains_any: keywords } }] : []),
    ...(org ? [{ requester_org: org }] : []),
    ...(conditionField && conditionValue ? [{ field: conditionField, op: 'in', value: [conditionValue] }] : []),
  ] };
  useEffect(() => {
    let live = true;
    learningApi.orgs().then((result) => { if (live) setOrgs(result.orgs); }, () => { if (live) setOrgError('요청 조직 목록을 불러오지 못했습니다.'); });
    return () => { live = false; };
  }, []);
  function addKeyword() {
    const added = keyword.split(',').map((part) => part.trim()).filter(Boolean);
    if (keywords.length + added.length > 20) { setError('키워드는 최대 20개입니다.'); return; }
    setKeywords([...keywords, ...added]); setKeyword(''); setError('');
  }
  function submit(event: React.FormEvent) {
    event.preventDefault();
    try {
      if (!direct && keyword.trim()) { setError('입력한 키워드를 먼저 추가해 주세요.'); return; }
      const parsed = direct ? JSON.parse(scope) : formScope;
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
    <fieldset disabled={direct || busy}><legend>제안 범위</legend>
      <label className="learning-field">원문 키워드<input aria-label="원문 키워드" value={keyword} onChange={(e) => { setKeyword(e.target.value); }} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addKeyword(); } }} /></label>
      <button type="button" onClick={addKeyword} disabled={!keyword.trim()}>키워드 추가</button>
      <div>{keywords.map((item, index) => <button type="button" key={index} aria-label={`키워드 ${item} 삭제`} onClick={() => setKeywords(keywords.filter((_, i) => i !== index))}>{item} ×</button>)}</div>
      <small>하나라도 포함되면 적용 · 대소문자·띄어쓰기 무시 · 최대 20개</small>
      <label className="learning-field">요청 조직<select aria-label="요청 조직" value={org} onChange={(e) => setOrg(e.target.value)}><option value="">모든 조직</option>{orgs.map((item) => <option value={item.id} key={item.id}>{orgLabel(item)}</option>)}</select></label>
      <label className="learning-field">조건 판단 항목<select aria-label="조건 판단 항목" value={conditionField} onChange={(e) => { setConditionField(e.target.value); setConditionValue(''); }}><option value="">판단 조건 없음</option>{Object.keys(values).map((key) => <option value={key} key={key}>{fieldLabel(key)}</option>)}</select></label>
      {conditionField && <label className="learning-field">조건 판단 값<select aria-label="조건 판단 값" value={conditionValue} onChange={(e) => setConditionValue(e.target.value)}><option value="">선택해 주세요</option>{({ ...values, feasibility: ['가능', ...values.feasibility], urgency: ['긴급', '일반', '판단 보류'] }[conditionField] || []).map((item) => <option key={item}>{item}</option>)}</select></label>}
    </fieldset>
    {orgError && <p role="alert">{orgError}</p>}
    <details><summary>고급: 조건 JSON</summary><label className="learning-field">제안 범위<textarea aria-label="제안 범위" rows={4} value={direct ? scope : JSON.stringify(formScope, null, 2)} onChange={(e) => { setDirect(true); setScope(e.target.value); }} /><small>예: {JSON.stringify({ all: orgs.length ? [{ requester_org: orgs[0].id }] : [] })} · 빈 조건은 모든 요청</small></label>{direct && <><p>JSON 직접 편집 중</p><button type="button" onClick={() => setDirect(false)}>조건 폼으로 돌아가기</button></>}</details>
    <p>키워드 규칙도 승인 → 섀도 검증 → 게시를 거쳐야 실행에 쓰입니다.</p>
    <label className="learning-field">제안 사유<textarea aria-label="제안 사유" maxLength={3000} required value={reason} onChange={(e) => setReason(e.target.value)} /></label>
    {error && <p role="alert">{error}</p>}
    <button type="submit" className="ui-button primary" disabled={busy || loading || !reason.trim()}>후보 제안 저장</button>
    <button type="button" className="ui-button secondary" onClick={onClose} disabled={busy}>닫기</button>
  </form>;
}
