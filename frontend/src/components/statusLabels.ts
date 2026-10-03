import type { StatusKind } from './index';

const labels: Record<string, { label: string; kind: StatusKind }> = {
  대기: { label: '대기', kind: 'pending' },
  진행: { label: '진행 중', kind: 'progress' },
  완료: { label: '완료', kind: 'success' },
  막힘: { label: '막힘', kind: 'review' },
  '검토 대기': { label: '검토 대기', kind: 'review' },
  '배정 완료': { label: '배정 완료', kind: 'success' },
  '보완 필요': { label: '보완 필요', kind: 'review' },
  실패: { label: '실패', kind: 'failure' },
  received: { label: '접수됨', kind: 'pending' },
  draft: { label: '초안', kind: 'pending' },
  pending: { label: '대기', kind: 'pending' },
  running: { label: '진행 중', kind: 'progress' },
  judging: { label: '판단 중', kind: 'progress' },
  committed: { label: '저장 완료', kind: 'success' },
  judgment_pending: { label: '판단 대기', kind: 'pending' },
  needs_file_decision: { label: '파일 결정 필요', kind: 'review' },
  review_pending: { label: '검토 대기', kind: 'review' },
  auto_assign_eligible: { label: '자동 배정 가능', kind: 'success' },
  assigned: { label: '배정됨', kind: 'success' },
  rejected: { label: '반려됨', kind: 'failure' },
  failed: { label: '실패', kind: 'failure' },
  cancelled: { label: '취소됨', kind: 'skipped' },
  superseded: { label: '이전 버전', kind: 'skipped' },
  completed: { label: '완료', kind: 'success' },
  succeeded: { label: '성공', kind: 'success' },
  success: { label: '성공', kind: 'success' },
  judgment_saved: { label: '판단 저장 완료', kind: 'success' },
  waiting_human: { label: '사람 검토 대기', kind: 'review' },
  skipped: { label: '건너뜀', kind: 'skipped' },
  interrupted: { label: '중단됨', kind: 'failure' },
  lost: { label: '소유권 상실', kind: 'failure' },
  undetermined: { label: '미확정', kind: 'review' },
  active: { label: '활성', kind: 'success' },
  validating: { label: '검증 중', kind: 'progress' },
  validated: { label: '검증 완료', kind: 'success' },
  published: { label: '게시됨', kind: 'success' },
  stopped: { label: '중단됨', kind: 'skipped' },
  reverted: { label: '되돌림', kind: 'skipped' },
  approved: { label: '승인됨', kind: 'success' },
  not_found: { label: '찾을 수 없음', kind: 'failure' },
  info_requested: { label: '보완 필요', kind: 'review' },
  needs_info: { label: '보완 필요', kind: 'review' },
  '반려': { label: '반려됨', kind: 'failure' },
  approved_with_changes: { label: '수정 승인됨', kind: 'success' },
  waiting: { label: '대기', kind: 'pending' },
};

export const roleLabels: Record<string, string> = { requester: '요청자', reviewer: '검토자', team_member: '팀 담당자', assignee: '팀 담당자', operator: '운영자', policy_editor: '정책 편집자', rule_admin: '규칙 관리자' };
export const roleLabel = (role: string) => roleLabels[role] ?? role;

export const reviewActionLabels: Record<string, string> = { approve: '승인', approve_with_changes: '수정 승인', reject: '반려', request_info: '정보 요청' };
export const reviewActionLabel = (action: string) => reviewActionLabels[action] ?? action;

export const attachmentReasonLabels: Record<string, string> = {
  unsupported_type: '지원하지 않는 형식입니다. PDF·DOCX·MD로 다시 저장해 첨부하거나 제외하세요.',
  corrupted: '파일이 손상되어 읽을 수 없습니다. 다시 저장해 첨부하거나 제외하세요.',
  encrypted: '암호가 걸린 파일입니다. 암호를 해제해 다시 첨부하거나 제외하세요.',
  too_large: '파일 크기 제한을 넘었습니다. 줄여서 다시 첨부하거나 제외하세요.',
  memory_limit: '파일이 너무 커서 읽지 못했습니다. 나누어 첨부하거나 제외하세요.',
  timeout: '읽는 데 시간이 너무 오래 걸렸습니다. 다시 첨부하거나 제외하세요.',
  scanned_no_text: '글자를 읽을 수 없는 스캔 문서입니다. 텍스트가 있는 파일로 바꾸어 첨부하거나 제외하세요.',
  input_limit_exceeded: '첨부 개수 또는 합계 크기 제한을 넘었습니다.',
};
export const attachmentReasonLabel = (reason?: string | null) => (reason ? attachmentReasonLabels[reason] ?? '읽지 못했습니다. 다시 첨부하거나 제외하세요.' : '읽지 못했습니다. 다시 첨부하거나 제외하세요.');

const exactErrors: Record<string, string> = {
  'Insufficient role': '이 화면을 사용할 권한이 없습니다.',
  'requester role required': '요청자 권한이 필요합니다.',
  'Request not found': '요청을 찾을 수 없습니다.',
  'Run not found': '실행을 찾을 수 없습니다.',
  'Step not found': '실행 단계를 찾을 수 없습니다.',
  'Review not found': '검토를 찾을 수 없습니다.',
  'Candidate not found': '후보를 찾을 수 없습니다.',
  'Evidence not found': '근거 원문을 찾을 수 없습니다.',
  'Node not found': '맵 항목을 찾을 수 없습니다.',
  'revision conflict': '다른 사용자가 먼저 변경했습니다. 최신 상태를 확인해 주세요.',
  'Idempotency-Key payload conflict': '같은 요청이 다른 내용으로 이미 처리되었습니다.',
  'Invalid email or password': '이메일 또는 암호가 올바르지 않습니다.',
  'Login temporarily unavailable': '로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.',
  'CSRF validation failed': '세션이 만료되었습니다. 다시 로그인해 주세요.',
  'request persistence unavailable': '저장소에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.',
  'SSE connection limit reached': '실시간 연결 수 한도에 도달했습니다.',
  'from must be before to': '시작 시각은 종료 시각보다 앞서야 합니다.',
  'Invalid ISO 8601 timestamp': '날짜 형식이 올바르지 않습니다.',
};
/** Replace backend English/internal-code messages with user-facing Korean; unknown text passes through. */
export function localizeError(message: string): string {
  if (exactErrors[message]) return exactErrors[message];
  if (/thresholds must be between 0 and 1/.test(message)) return '임계값은 0과 1 사이여야 합니다.';
  if (/^[A-Z][A-Z_]+(:|$)/.test(message)) return '입력 값이 올바르지 않습니다. 기술 상세를 확인해 주세요.';
  return message;
}

/** Korean label when the status is known; otherwise the stored text (already Korean for e.g. '제안'). */
export const statusText = (status?: string | null) => (status ? labels[status]?.label ?? status : '');

export function getStatusLabel(status: string): string {
  return labels[status]?.label ?? `알 수 없는 상태 · ${status}`;
}

export function getStatusPresentation(status: string): { label: string; status: StatusKind; known: boolean } {
  const mapped = labels[status];
  return mapped ? { label: mapped.label, status: mapped.kind, known: true } : { label: `알 수 없는 상태 · ${status}`, status: 'pending', known: false };
}
