/** Korean labels for internal codes shown on regular screens. Raw codes belong in a collapsed "자세히" block only. */

export const fieldLabels: Record<string, string> = { ai_need: 'AI 필요성', feasibility: '개발 가능성', urgency: '긴급도', lead_org: '담당 조직 · 주관' };
export const fieldLabel = (field: string) => fieldLabels[field] || field;

const questionLabels: Record<string, string> = {
  ...fieldLabels,
  ai_team_involvement: 'AI팀 참여', it_team_involvement: 'IT팀 참여', business_involvement: '현업 참여',
  clinical_safety: '임상 안전', pharmacovigilance: '약물 감시', regulatory: '규제 대응', review_signal: '검토 필요도',
};
export const questionLabel = (id: string) => questionLabels[id] || id;

const outputTypeLabels: Record<string, string> = { choice: '선택형', noul: '확률형', score: '점수형' };
export const outputTypeLabel = (type: string) => outputTypeLabels[String(type).toLowerCase()] || String(type);

const blockReasonLabels: Record<string, string> = {
  feasibility_unresolved: '개발 가능성 또는 수행 전제가 아직 해결되지 않았습니다.',
  predecessor_incomplete: '선행 업무가 아직 완료되지 않았습니다.',
  draft_reason: '검토에서 확인할 전제 조건이 남아 있습니다.',
  undetermined_draft: '담당 조직이나 산출물이 아직 정해지지 않았습니다.',
};
export const blockReasonLabel = (code: string) => blockReasonLabels[code] || code;

/** Review/eligibility reasons are Korean sentences with an embedded internal key ("Choice confidence 미충족: ai_need/lead_org"). */
const reasonPrefixes: Array<[string, string]> = [
  ['Choice confidence 미충족', '선택 확신도 미충족'], ['미정 분류', '분류 미확정'], ['필수 검토', '필수 검토'], ['Noul 참여 불확실', '참여 여부 불확실'],
];
const reasonKeys: Record<string, string> = { ...questionLabels, urgent: '긴급 요청' };
export function reviewReasonLabel(text: string): string {
  const hit = reasonPrefixes.find(([prefix]) => text.startsWith(`${prefix}: `));
  if (!hit) return text;
  const keys = text.slice(hit[0].length + 2).split('/').map((key) => reasonKeys[key.trim()] || key.trim());
  return `${hit[1]}: ${keys.join(' · ')}`;
}

const collectionIssueLabels: Record<string, string> = {
  invalid_collector_heartbeat: '수집기 상태 기록이 올바르지 않습니다.',
  collector_stopped: '수집기가 멈춰 있습니다.',
  metrics_store_unavailable: '지표 저장소에 접근할 수 없습니다.',
  damaged_or_truncated_journal: '일부 기록이 손상되었거나 잘렸습니다.',
  collector_gap_30d: '최근 30일 안에 수집이 끊긴 구간이 있습니다.',
};
export const collectionIssueLabel = (code: string) => collectionIssueLabels[code] || code;
const intervalKindLabels: Record<string, string> = { damaged_line: '손상된 기록', truncated_line: '잘린 기록', collector_gap: '수집 중단' };
export const intervalKindLabel = (kind: string) => intervalKindLabels[kind] || collectionIssueLabels[kind] || kind;

export function sloReasonLabel(text: string | null | undefined): string {
  if (!text) return '';
  if (/^Less than 30 days of complete observation/.test(text)) return '완전한 관측이 30일에 못 미쳐 아직 검증할 수 없습니다.';
  if (/^Incomplete or insufficient samples/.test(text)) return '표본이 불완전하거나 부족해 검증할 수 없습니다.';
  return text;
}

const alertKindLabels: Record<string, string> = {
  worker_stopped: '작업자 프로세스가 멈췄습니다', api_stopped: 'API 서버가 응답하지 않습니다', collector_stopped: '수집기가 멈췄습니다',
  slo_burn: '서비스 수준 목표 소진 속도가 높습니다', metrics_gap: '지표 수집이 끊겼습니다',
};
export const alertKindLabel = (kind: string) => alertKindLabels[kind] || '운영 알림';

export const ruleDecisionLabels: Record<string, string> = { approve: '승인', approve_with_scope_change: '범위 수정 후 승인', reject: '기각' };
export const ruleDecisionLabel = (action: string) => ruleDecisionLabels[action] || action;

const n = (value: unknown) => Number(value);
/** Position of a cited span in plain Korean; the raw location object stays in "자세히". */
export function locationLabel(location: unknown): string {
  const l = (location && typeof location === 'object' ? location : {}) as Record<string, unknown>;
  if (l.page !== undefined) return `${n(l.page)}쪽`;
  if (l.line_start !== undefined) { const start = n(l.line_start), end = n(l.line_end ?? l.line_start); return end > start ? `${start}–${end}행` : `${start}행`; }
  if (l.paragraph !== undefined) return l.sentence !== undefined ? `문단 ${n(l.paragraph) + 1} · 문장 ${n(l.sentence) + 1}` : `문단 ${n(l.paragraph) + 1}`;
  return '위치 정보 없음';
}

/** Readable value of a model output (choice / probability / score). */
export function outputValueLabel(output: { value?: unknown; noul?: unknown; confidence?: unknown }): string {
  const pct = (v: unknown) => typeof v === 'number' ? `${Math.round(v * 100)}%` : String(v);
  if (typeof output.value === 'string' && output.value !== '') return output.confidence !== undefined && output.confidence !== null ? `${output.value} (확신도 ${pct(output.confidence)})` : output.value;
  if (output.noul !== undefined && output.noul !== null) return `확률 ${pct(output.noul)}`;
  if (output.value !== undefined && output.value !== null) return typeof output.value === 'boolean' ? (output.value ? '예' : '아니오') : pct(output.value);
  return output.confidence !== undefined && output.confidence !== null ? `확신도 ${pct(output.confidence)}` : '—';
}
