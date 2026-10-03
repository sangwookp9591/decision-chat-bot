import { describe, expect, it } from 'vitest';
import { alertKindLabel, blockReasonLabel, collectionIssueLabel, fieldLabel, questionLabel, reviewReasonLabel, sloReasonLabel } from './labels';

describe('shared labels (P4-05)', () => {
  it('translates codes and passes unknown text through', () => {
    expect(blockReasonLabel('feasibility_unresolved')).toContain('개발 가능성');
    expect(blockReasonLabel('weird_code')).toBe('weird_code');
    expect(fieldLabel('lead_org')).toBe('담당 조직 · 주관');
    expect(questionLabel('ai_team_involvement')).toBe('AI팀 참여');
    expect(reviewReasonLabel('Choice confidence 미충족: ai_need/feasibility/lead_org')).toBe('선택 확신도 미충족: AI 필요성 · 개발 가능성 · 담당 조직 · 주관');
    expect(reviewReasonLabel('필수 검토: urgent')).toBe('필수 검토: 긴급 요청');
    expect(reviewReasonLabel('정보 부족')).toBe('정보 부족');
    expect(collectionIssueLabel('collector_stopped')).toContain('수집기');
    expect(alertKindLabel('worker_stopped')).toContain('작업자');
    expect(sloReasonLabel('Less than 30 days of complete observation')).toContain('30일');
  });
});
