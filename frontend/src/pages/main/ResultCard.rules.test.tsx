import '@testing-library/jest-dom/vitest';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { Result, ResultBrief } from './ResultCard';
import { requestApi, type Judgment } from '../../api/requests';
import { ruleOverrides, ruleLabel } from '../../lib/ruleEffects';

vi.mock('../../api/requests', () => ({ requestApi: { evidence: vi.fn(), document: vi.fn() } }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const effect = { rule_version: 'R-LEAD_ORG-03@1', source: 'rule:R-LEAD_ORG-03@v1', target: 'lead_org', effect: 'rule', outcome: 'used', before: 'AI팀', after: 'IT팀', matches: [{ unit_id: 'esp_7', char_start: 0, char_end: 3, keyword: 'VPN' }] };
const judgment = { id: 'j', request_id: 'req', revision_id: 'rev', run_id: 'run', classifications: { lead_org: 'IT팀' }, rule_effects: [effect], summary: { text: '요약' }, mode: 'live', outputs: [{ id: 'out', question_id: 'lead_org', type: 'choice', value: 'AI팀', evidence: [{ id: 'model', location: {} }] }], draft_tasks: [], review_reasons: [], review: null } as unknown as Judgment;

it.each(['brief', 'detail'])('shows rule and preserves original model evidence in %s', (kind) => {
  render(kind === 'brief' ? <ResultBrief judgment={judgment} onEvidence={() => {}} onDetail={() => {}} /> : <Result judgment={judgment} runs={null} onEvidence={() => {}} />);
  expect(screen.getByText('규칙 적용 · R-LEAD_ORG-03 v1')).toBeInTheDocument();
  expect(screen.getByText('모델 판단 AI팀 → 규칙 IT팀')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '규칙 근거 · ‘VPN’' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '모델 원판단(AI팀) 근거 열기' })).toBeInTheDocument();
  expect(screen.getByText('적용된 규칙 1건')).toBeInTheDocument();
});

it('uses evidence attachment ID to open and anchor the persisted source unit', async () => {
  vi.mocked(requestApi.evidence).mockResolvedValue({ id: 'esp_7', attachment_id: 'att_2', location: {} });
  vi.mocked(requestApi.document).mockResolvedValue({ request_id: 'req', revision: 1, revision_id: 'rev', source: 'att_2', kind: 'md', filename: 'vpn.md', can_read_source: true, units: [{ unit_id: 'esp_7', order: 0, location: {}, char_start: 0, char_end: 6, text: 'VPN 접속' }] });
  Element.prototype.scrollTo = vi.fn();
  render(<ResultBrief judgment={judgment} onEvidence={() => {}} onDetail={() => {}} />);
  fireEvent.click(screen.getByRole('button', { name: '규칙 근거 · ‘VPN’' }));
  expect(await screen.findByText('VPN 접속')).toBeInTheDocument();
  expect(requestApi.evidence).toHaveBeenCalledWith('req', 'esp_7');
  expect(requestApi.document).toHaveBeenCalledWith('req', 'rev', 'att_2');
  expect(document.querySelector('[data-unit-id="esp_7"]')).toHaveAttribute('aria-current', 'location');
});

it('handles old effects, unchanged values, conflict and require_review without claiming a classification override', () => {
  expect(ruleLabel({ ...effect, source: undefined })).toBe('R-LEAD_ORG-03 v1');
  expect(ruleOverrides([{ ...effect, target: undefined }, { ...effect, before: 'IT팀' }, { ...effect, outcome: 'conflict' }, { ...effect, target: 'review_route' }])).toEqual({});
});
