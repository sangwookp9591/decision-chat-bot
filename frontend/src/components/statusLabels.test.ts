import { describe, expect, it } from 'vitest';
import { attachmentReasonLabel, localizeError, reviewActionLabel, roleLabel, statusText } from './statusLabels';

describe('shared Korean labels (P3-13)', () => {
  it('labels every server role', () => {
    expect(['requester', 'reviewer', 'team_member', 'operator', 'policy_editor', 'rule_admin'].map(roleLabel)).toEqual(['요청자', '검토자', '팀 담당자', '운영자', '정책 편집자', '규칙 관리자']);
  });
  it('translates internal codes, review actions and statuses', () => {
    expect(reviewActionLabel('request_info')).toBe('정보 요청'); expect(reviewActionLabel('reject')).toBe('반려');
    expect(statusText('published')).toBe('게시됨'); expect(statusText('validated')).toBe('검증 완료'); expect(statusText('제안')).toBe('제안');
    expect(statusText('used')).toBe('적용됨'); expect(statusText('out_of_scope')).toBe('범위 밖(미적용)');
    expect(attachmentReasonLabel('unsupported_type')).toContain('다시 저장해 첨부하거나 제외');
    expect(attachmentReasonLabel('something_new')).not.toMatch(/something_new/);
  });
  it('localizes backend error strings and hides internal codes', () => {
    expect(localizeError('Insufficient role')).toBe('이 화면을 사용할 권한이 없습니다.');
    expect(localizeError('Request not found')).toBe('요청을 찾을 수 없습니다.');
    expect(localizeError('SCHEMA_INVALID: Value error, thresholds must be between 0 and 1')).toBe('임계값은 0과 1 사이여야 합니다.');
    expect(localizeError('SOME_CODE: detail')).not.toMatch(/SOME_CODE/);
    expect(localizeError('이미 한국어인 안내')).toBe('이미 한국어인 안내');
  });
});
