import { describe, expect, it } from 'vitest';
import { alertKindLabel, blockReasonLabel, collectionIssueLabel, fieldLabel, questionLabel, reviewReasonLabel, sloReasonLabel, mapNodeTitleLabel, policyFieldLabel, displayCodeLabel, comparisonConditionsLabel } from './labels';

describe('shared labels (P4-05)', () => {
  it('translates codes and passes unknown text through', () => {
    expect(blockReasonLabel('feasibility_unresolved')).toContain('개발 가능성');
    expect(blockReasonLabel('weird_code')).toBe('weird_code');
    expect(fieldLabel('lead_org')).toBe('담당 조직 · 주관');
    expect(questionLabel('ai_team_involvement')).toBe('AI팀 참여 확률');
    expect(questionLabel('clinical_safety')).toBe('임상·안전 위험 확률');
    expect(questionLabel('business_involvement')).toBe('현업 참여 확률');
    expect(policyFieldLabel('risk_clear_max')).toBe('위험 없음 확인 상한');
    expect(mapNodeTitleLabel('Jev · lead_org')).toBe('Jev · 담당 조직 · 주관');
    expect(mapNodeTitleLabel('검토 결정 · request_info')).toBe('검토 결정 · 정보 요청');
    expect(mapNodeTitleLabel('규칙 결정 · approve')).toBe('규칙 결정 · 승인');
    expect(displayCodeLabel('APPLIED used/out_of_scope · risk_clear_max')).toBe('적용 적용됨/범위 밖(미적용) · 위험 없음 확인 상한');
    expect(reviewReasonLabel('Choice confidence 미충족: ai_need/feasibility/lead_org')).toBe('선택 확신도 미충족: AI 필요성 · 개발 가능성 · 담당 조직 · 주관');
    expect(reviewReasonLabel('필수 검토: urgent')).toBe('필수 검토: 긴급 요청');
    expect(reviewReasonLabel('정보 부족')).toBe('정보 부족');
    expect(collectionIssueLabel('collector_stopped')).toContain('수집기');
    expect(alertKindLabel('worker_stopped')).toContain('작업자');
    expect(sloReasonLabel('Less than 30 days of complete observation')).toContain('30일');
  });
});

describe('comparisonConditionsLabel', () => {
  it('rewrites the raw server sentence (APPLIED/shadow) into plain Korean', () => {
    const text = comparisonConditionsLabel('게시 시각 전후 동일 길이 창의 실제 Run; 게시 후 APPLIED used/out_of_scope 집단; shadow 제외');
    expect(text).toBe('실제 실행 / 규칙 적용·범위 밖 집단 / 비교 검증 실행 제외');
    expect(text).not.toMatch(/shadow|APPLIED|Run/);
  });
});
