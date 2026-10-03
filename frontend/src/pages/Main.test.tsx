import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Result } from './Main';
import type { Judgment } from '../api/requests';

const judgment: Judgment = {
  id: 'j1', request_id: 'req_1', revision_id: 'rev_1', run_id: 'run_1',
  classifications: { ai_need: '정보 부족', feasibility: '조건부 가능', urgency: '판단 보류', lead_org: '미정' },
  risk_confirmed: false, risks: [], summary: { text: '요약 발췌', author: 'code:extractive@1' }, author: 'code:extractive@1',
  versions: {}, mode: 'live', outputs: [
    { id: 'o1', question_id: 'ai_need', type: 'Choice', value: '정보 부족', confidence: 0.72, evidence: [] },
    { id: 'o2', question_id: 'urgency', type: 'Noul', value: 'judgment_hold', noul: 0.41, evidence: [] },
  ], draft_tasks: [], review_reasons: ['정보가 부족합니다'], review: { status: 'pending' },
};

describe('judgment result', () => {
  it('shows uncertainty as a separate scale value and labels Jev signals distinctly', () => {
    const { container } = render(<Result judgment={judgment} runs={null} onEvidence={() => undefined} />);
    expect(container.querySelector('.uncertain-result')?.textContent).toContain('정보 부족');
    expect(screen.getByText('판단 보류')).toBeTruthy();
    expect(screen.getByText('Choice confidence 72%')).toBeTruthy();
    expect(screen.getByText('Noul 확률 0.41')).toBeTruthy();
  });
});
