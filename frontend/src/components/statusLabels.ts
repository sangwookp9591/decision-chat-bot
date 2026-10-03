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
};

export function getStatusLabel(status: string): string {
  return labels[status]?.label ?? `알 수 없는 상태 · ${status}`;
}

export function getStatusPresentation(status: string): { label: string; status: StatusKind; known: boolean } {
  const mapped = labels[status];
  return mapped ? { label: mapped.label, status: mapped.kind, known: true } : { label: `알 수 없는 상태 · ${status}`, status: 'pending', known: false };
}
