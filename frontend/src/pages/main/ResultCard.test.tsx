import '@testing-library/jest-dom/vitest';
import { cleanup, render } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import type { Judgment } from '../../api/requests';
import { Result, ResultBrief } from './ResultCard';

const judgment = { id: 'j1', request_id: 'req_1', revision_id: 'rev_1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1', run_id: 'run_2bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb2', classifications: { ai_need: '필요', feasibility: '가능', urgency: '일반', lead_org: 'AI팀' }, risk_confirmed: false, risks: [], summary: { text: '요약', author: 'x' }, author: 'x', versions: {}, mode: 'live', outputs: [], draft_tasks: [], review_reasons: [], review: null } as unknown as Judgment;
afterEach(cleanup);

describe('judgment result ids', () => {
  it('keeps raw run/revision ids out of the conversation card', () => {
    const { container } = render(<ResultBrief judgment={judgment} onEvidence={() => {}} onDetail={() => {}} />);
    expect(container.textContent).not.toContain(judgment.run_id);
    expect(container.textContent).not.toContain(judgment.revision_id);
  });
  it('shows the ids as short chips inside the detail view', () => {
    const { container } = render(<Result judgment={judgment} runs={null} onEvidence={() => {}} />);
    expect(container.querySelectorAll('code.short-id').length).toBeGreaterThanOrEqual(2);
    expect(container.querySelector('code:not(.short-id)')).toBeNull();
  });
});
