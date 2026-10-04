/** Korean labels for internal codes shown on regular screens. Raw codes belong in a collapsed "자세히" block only. */

export const fieldLabels: Record<string, string> = { ai_need: 'AI 필요성', feasibility: '개발 가능성', urgency: '긴급도', lead_org: '담당 조직 · 주관' };
export const fieldLabel = (field: string) => fieldLabels[field] || field;

const questionLabels: Record<string, string> = {
  ...fieldLabels,
  ai_team_involvement: 'AI팀 참여 확률', it_team_involvement: 'IT팀 참여 확률', business_involvement: '현업 참여 확률',
  clinical_safety: '임상·안전 위험 확률', pharmacovigilance: '약물 감시 위험 확률', regulatory: '규제 대응 위험 확률', review_signal: '검토 필요도',
};
export const questionLabel = (id: string) => questionLabels[id] || id;

/** Policy editor fields: Korean name + one-line meaning; the internal key stays in the collapsed 기술 상세. */
export const policyFieldInfo: Record<string, { label: string; hint: string }> = {
  schema_version: { label: '정책 형식 버전', hint: '정책 문서의 형식 버전입니다. 직접 바꿀 수 없습니다.' },
  auto_assign: { label: '승인 없는 자동 배정', hint: '허용되지 않는 설정이라 잠겨 있습니다.' },
  choice_confidence_thresholds: { label: '선택형 판단 최소 확신도', hint: '이 값보다 확신도가 낮으면 사람 검토로 넘깁니다. 항목마다 0~1 사이로 정합니다.' },
  noul_probability_thresholds: { label: '참여 확률 기준', hint: '팀·위험 참여 여부를 확정하는 확률 기준입니다. 0~1 사이로 정합니다.' },
  risk_clear_max: { label: '위험 없음 확인 상한', hint: '위험 확률이 이 값 이하일 때만 “위험 없음”으로 봅니다.' },
  reviewer_groups: { label: '검토자 그룹', hint: '검토 분류별로 담당할 검토자 그룹을 지정합니다.' },
  limits: { label: '처리 한도', hint: '요청 한 건에 쓸 수 있는 분량·시간 등의 상한입니다.' },
  evidence_noul_threshold: { label: '근거 연결 확률 기준', hint: '근거로 인정할 최소 확률입니다. 0~1 사이로 정합니다.' },
  catalog_noul_threshold: { label: '업무 목록 매칭 확률 기준', hint: '업무 목록과 일치한다고 볼 최소 확률입니다. 0~1 사이로 정합니다.' },
  feature_flags: { label: '기능 사용 여부', hint: '기능별로 켜고 끄는 스위치입니다.' },
  rules: { label: '학습 규칙', hint: '규칙 학습 화면에서 관리합니다. 여기서는 읽기만 가능합니다.' },
};
export const policyFieldLabel = (field: string) => policyFieldInfo[field]?.label || fieldLabel(field);
export const policyFieldHint = (field: string) => policyFieldInfo[field]?.hint || '';
const policyFieldLabels = { risk_clear_max: policyFieldInfo.risk_clear_max.label };

/** Translate known field/action tokens embedded in graph titles while keeping the surrounding title readable. */
export function mapNodeTitleLabel(title: string): string {
  return title.replace(/\b(ai_need|feasibility|urgency|lead_org|ai_team_involvement|it_team_involvement|business_involvement|clinical_safety|pharmacovigilance|regulatory|review_signal|approve_with_scope_change|approve_with_changes|request_info|approve|reject)\b/g,
    (code) => ({ approve: '승인', reject: '반려', request_info: '정보 요청', approve_with_scope_change: '범위 수정 후 승인', approve_with_changes: '수정 승인' }[code] || questionLabels[code] || fieldLabel(code)));
}
export function displayCodeLabel(text: string): string {
  return text.replace(/\b(APPLIED|risk_clear_max|used|out_of_scope|approve_with_scope_change|approve_with_changes|request_info|approve|reject)\b/g,
    (code) => ({ APPLIED: '적용', risk_clear_max: policyFieldLabels.risk_clear_max, used: '적용됨', out_of_scope: '범위 밖(미적용)', approve: '승인', reject: '반려', request_info: '정보 요청', approve_with_scope_change: '범위 수정 후 승인', approve_with_changes: '수정 승인' }[code] || code));
}

/** 학습 효과 비교 조건 설명: 서버의 원시 표현(APPLIED/shadow)을 문장 단위로 한국어화한다. */
export function comparisonConditionsLabel(text: string): string {
  return /shadow|APPLIED|out_of_scope/.test(text) ? '실제 실행 / 규칙 적용·범위 밖 집단 / 비교 검증 실행 제외' : displayCodeLabel(text);
}

const outputTypeLabels: Record<string, string> = { choice: '선택형', noul: '확률형', score: '점수형' };
export const outputTypeLabel = (type: string) => outputTypeLabels[String(type).toLowerCase()] || String(type);

const blockReasonLabels: Record<string, string> = {
  feasibility_unresolved: '개발 가능성 또는 수행 전제가 아직 해결되지 않았습니다.',
  predecessor_incomplete: '선행 업무가 아직 완료되지 않았습니다.',
  draft_reason: '검토에서 확인할 전제 조건이 남아 있습니다.',
  undetermined_draft: '담당 조직이나 산출물이 아직 정해지지 않았습니다.',
};
export const blockReasonLabel = (code: string) => blockReasonLabels[code] || displayCodeLabel(code);

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

/** Evaluation-label screen: fields a labeler edits, and the agreement state between labelers. */
export const evaluationFieldInfo: Record<string, { label: string; hint: string }> = {
  ai_need: { label: 'AI 필요성', hint: 'AI가 필요한 요청인지 (필요·불필요·혼합)' },
  feasibility: { label: '개발 가능성', hint: '지금 개발할 수 있는지 (가능·조건부 가능·현재 불가)' },
  urgency: { label: '긴급도', hint: '긴급 대응이 필요한지 (긴급·일반)' },
  team_set: { label: '참여 팀 구성', hint: '일을 함께 맡아야 할 팀의 조합' },
  risk_areas: { label: '위험 영역', hint: '검토가 필요한 위험 분야 (임상·안전·규제 등)' },
};
export const evaluationFieldLabel = (field: string) => evaluationFieldInfo[field]?.label || fieldLabel(field);
const consensusLabels: Record<string, string> = {
  consensus_required: '검토자 간 의견 불일치 — 합의가 필요합니다',
  agreed: '검토자 의견 일치', resolved: '합의 완료', unlabeled: '아직 라벨 없음', single_label: '검토자 1명이 라벨함 — 다른 검토자 확인 대기',
};
export const consensusLabel = (state: string) => consensusLabels[state] || '확인 필요한 상태';
const decisionStatusLabels: Record<string, string> = { confirmed: '확정', deferred: '보류' };
export const decisionStatusLabel = (status: string) => decisionStatusLabels[status] || status;
