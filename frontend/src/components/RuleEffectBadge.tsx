import { useState } from 'react';
import { requestApi } from '../api/requests';
import { ruleLabel, type RuleEffect } from '../lib/ruleEffects';
import { EvidenceViewer, type ViewerTarget } from './EvidenceViewer';

export function RuleEffectBadge({ effect, requestId, revision }: { effect: RuleEffect; requestId: string; revision: string }) {
  const [target, setTarget] = useState<ViewerTarget | null>(null);
  const [error, setError] = useState('');
  async function open(unitId: string) {
    setError('');
    try {
      const evidence = await requestApi.evidence(requestId, unitId);
      setTarget({ requestId, revision, source: evidence.attachment_id || 'chat', unitId, title: '규칙 근거 원문' });
    } catch { setError('규칙 근거를 불러오지 못했습니다.'); }
  }
  return <div className="rule-effect"><span className="environment-badge">규칙 적용 · {ruleLabel(effect)}</span>
    <p>모델 판단 {String(effect.before)} → 규칙 {String(effect.after)}</p>
    <div className="evidence-list">{(effect.matches || []).map((match, index) => <button type="button" key={`${match.unit_id}-${match.char_start}-${index}`} onClick={() => void open(match.unit_id)}>규칙 근거 · ‘{match.keyword}’</button>)}</div>
    {error && <p role="alert">{error}</p>}<EvidenceViewer target={target} onClose={() => setTarget(null)} />
  </div>;
}

export function AppliedRules({ effects = [] }: { effects?: RuleEffect[] }) {
  const used = effects.filter((effect) => effect.outcome === 'used');
  const other = effects.filter((effect) => ['conflict', 'blocked_by_invariant'].includes(effect.outcome));
  if (!used.length && !other.length) return null;
  return <details><summary>적용된 규칙 {used.length}건</summary><ul>{used.map((effect, index) => <li key={index}>{ruleLabel(effect)} · {effect.target || effect.effect} · {String(effect.after)}</li>)}</ul>
    {other.length > 0 && <details><summary>자세히</summary><ul>{other.map((effect, index) => <li key={index}>{ruleLabel(effect)} · {effect.outcome === 'conflict' ? '충돌' : '안전 조건으로 차단'}</li>)}</ul></details>}
  </details>;
}
