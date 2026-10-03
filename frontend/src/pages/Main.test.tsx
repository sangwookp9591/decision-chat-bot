import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { Main, Result } from './Main';
import { requestApi } from '../api/requests';

vi.mock('../api/requests', () => ({ requestApi: { detail: vi.fn(), list: vi.fn(), judgment: vi.fn(), runs: vi.fn(), reanalyze: vi.fn(), evidence: vi.fn(), document: vi.fn() } }));
vi.mock('../state/events', () => ({ useEventStream: () => ({ status: 'connected', lastSeq: 0 }) }));
vi.mock('../state/session', () => ({ useSession: () => ({ user: { id: 'u1', name: 'u1', roles: ['requester'] } }) }));
afterEach(cleanup);
const Where = () => <div data-testid="where">{useLocation().search}</div>;
const open = (url = '/') => render(<MemoryRouter initialEntries={[url]}><Main /><Where /></MemoryRouter>);
const detailOf = (status: string, extra: Record<string, unknown> = {}) => ({ request: { id: 'req_1', status, revision_number: 1, ...extra }, revisions: [{ id: 'rev_1', number: 1 }], attachments: [] });
function mockRequest(status: string, extra: Record<string, unknown> = {}) {
  vi.mocked(requestApi.list).mockResolvedValue({ items: [{ id: 'req_1', status }, { id: 'req_2', status: 'received' }] });
  vi.mocked(requestApi.detail).mockResolvedValue(detailOf(status, extra) as never);
  vi.mocked(requestApi.judgment).mockResolvedValue(judgmentFixture() as never);
  vi.mocked(requestApi.runs).mockResolvedValue({ active_run_id: 'run_1', runs: [{ id: 'run_1', status: 'succeeded', versions: {} }] });
}
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

const judgmentFixture = () => judgment;
describe('judgment result', () => {
  it('shows uncertainty as a separate scale value and labels Jev signals distinctly', () => {
    const { container } = render(<Result judgment={judgment} runs={null} onEvidence={() => undefined} />);
    expect(container.querySelector('.uncertain-result')?.textContent).toContain('정보 부족');
    expect(screen.getByText('판단 보류')).toBeTruthy();
    expect(screen.getByText('선택 신뢰도 72%')).toBeTruthy();
    expect(screen.getByText('Noul 확률 0.41')).toBeTruthy();
  });
});

describe('Main page UX (P3-02/05/11/13)', () => {
  it('restores the selected request from ?request_id= after a reload (P3-11)', async () => {
    mockRequest('judgment_saved');
    open('/?request_id=req_1');
    expect(await screen.findByRole('heading', { name: '분석 진행' })).toBeInTheDocument();
    expect(requestApi.detail).toHaveBeenCalledWith('req_1');
    expect(await screen.findByText('요약 발췌')).toBeInTheDocument();
  });
  it('puts the chosen request in the URL (P3-11)', async () => {
    mockRequest('judgment_saved');
    open('/');
    fireEvent.click(await screen.findByRole('button', { name: /req_2/ }));
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe('?request_id=req_2'));
  });
  it('shows the info request and a supplement submit for a request that needs more information (P3-02)', async () => {
    mockRequest('보완 필요', { info_requested: '사용 부서와 완료 희망일을 보완해 주세요', needed_info: JSON.stringify(['사용 부서와 완료 희망일을 보완해 주세요']) });
    open('/?request_id=req_1');
    const region = await screen.findByRole('region', { name: '보완 요청' });
    expect(region.textContent).toContain('사용 부서와 완료 희망일을 보완해 주세요');
    expect(screen.getByRole('button', { name: '보완 내용 제출 (새 revision)' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '요청 보내기' })).toBeNull();
    expect(screen.getAllByText('보완 필요 · 정보 요청').length).toBeGreaterThan(0);
    expect(screen.queryByText('검토 대기')).toBeNull();
  });
  it('shows rejected requests as rejected, not as waiting for review (P3-02)', async () => {
    mockRequest('반려');
    open('/?request_id=req_1');
    expect((await screen.findAllByText('반려됨')).length).toBeGreaterThan(0);
  });
  it('hands chat widget text to the intake form immediately and focuses it (P3-05)', async () => {
    mockRequest('judgment_saved');
    open('/');
    const field = await screen.findByLabelText('요청 내용');
    act(() => { window.dispatchEvent(new CustomEvent('chat:request', { detail: '채팅으로 추가한 회의실 검색 요청입니다' })); });
    await waitFor(() => expect(field).toHaveValue('채팅으로 추가한 회의실 검색 요청입니다'));
    await waitFor(() => expect(document.activeElement).toBe(field));
    expect(screen.getByRole('status').textContent).toContain('요청 입력에 옮겼습니다');
  });
  it('shows attachment failures with a recovery action in Korean (P3-13)', async () => {
    vi.mocked(requestApi.list).mockResolvedValue({ items: [] });
    vi.mocked(requestApi.detail).mockResolvedValue({ ...detailOf('needs_file_decision'), attachments: [{ id: 'att_1', filename: 'a.pdf', status: 'rejected', reason: 'unsupported_type' }] } as never);
    vi.mocked(requestApi.judgment).mockRejectedValue({ status: 404 });
    vi.mocked(requestApi.runs).mockResolvedValue({ active_run_id: null, runs: [] });
    open('/?request_id=req_1');
    expect((await screen.findByText(/a\.pdf — /)).textContent).toContain('다시 저장해 첨부하거나 제외');
    expect(screen.queryByText(/unsupported_type/)).toBeNull();
  });
});

describe('evidence viewer from the result card', () => {
  it('opens the source viewer on the cited attachment revision and highlights the cited unit', async () => {
    mockRequest('judgment_saved');
    const withEvidence = judgmentFixture();
    vi.mocked(requestApi.judgment).mockResolvedValue({ ...withEvidence, outputs: [{ id: 'o1', question_id: 'ai_need', type: 'Choice', value: '필요', confidence: 0.8, evidence: [{ id: 'esp_9', source: 'attachment', attachment_id: 'att_1', location: { page: 2 } }] }] } as never);
    vi.mocked(requestApi.document).mockResolvedValue({ request_id: 'req_1', revision: 1, revision_id: 'rev_1', source: 'att_1', kind: 'pdf', filename: 'a.pdf', can_read_source: true,
      units: [{ unit_id: 'esp_1', order: 0, location: { page: 1 }, char_start: 0, char_end: 3, text: '1쪽 본문' }, { unit_id: 'esp_9', order: 1, location: { page: 2 }, char_start: 3, char_end: 6, text: '2쪽 본문' }] });
    Element.prototype.scrollTo = vi.fn() as never;
    open('/?request_id=req_1');
    fireEvent.click(await screen.findByRole('button', { name: /첨부 · .*근거 열기/ }));
    expect(await screen.findByText('2쪽 본문')).toBeInTheDocument();
    expect(requestApi.document).toHaveBeenCalledWith('req_1', 'rev_1', 'att_1');
    expect(document.querySelector('[data-unit-id="esp_9"]')).toHaveAttribute('aria-current', 'location');
    expect(document.querySelector('[data-unit-id="esp_1"]')).not.toHaveAttribute('aria-current');
  });
});

describe('internal codes on the result card (P4-05)', () => {
  it('shows Korean review reasons and keeps raw codes out of the regular view', () => {
    const { container } = render(<Result judgment={{ ...judgment, review_reasons: ['Choice confidence 미충족: ai_need/feasibility/lead_org', '필수 검토: urgent'] }} runs={null} onEvidence={() => undefined} />);
    expect(container.textContent).toContain('선택 확신도 미충족: AI 필요성 · 개발 가능성 · 담당 조직 · 주관');
    expect(container.textContent).toContain('필수 검토: 긴급 요청');
    const visible = container.cloneNode(true) as HTMLElement; visible.querySelectorAll('details').forEach((node) => node.remove());
    expect(visible.textContent).not.toMatch(/ai_need|feasibility|lead_org|urgent/);
    expect(container.querySelector('details')?.textContent).toContain('ai_need/feasibility/lead_org');
  });

  it('shows each task once from the current draft and keeps the original in the comparison (P6-01)', () => {
    const task = (version: number, lead: string) => ({ id: `d${version}`, draft_task_id: 'draft-1', draft_version: version, title: '화면 개발', method: '일반 기술', lead_org: lead, collab_orgs: [], predecessors: [] });
    const withDrafts: Judgment = { ...judgment, draft_tasks: [task(2, '현업')], current_draft_version: 2, draft_versions: [
      { draft_version: 1, source: 'ai', created_by: 'ai', created_at: null, tasks: [task(1, 'IT팀')] },
      { draft_version: 2, source: 'reviewer', created_by: 'reviewer', created_at: null, tasks: [task(2, '현업')] }] };
    const { container } = render(<Result judgment={withDrafts} runs={null} onEvidence={() => undefined} />);
    expect(container.querySelectorAll('.result-summary > .task-row')).toHaveLength(1);
    expect(screen.getByRole('heading', { name: /업무 분담 \(v2 검토자 수정안\)/ })).toBeTruthy();
    const compare = container.querySelector('details.draft-compare') as HTMLElement;
    expect(compare.querySelector('summary')?.textContent).toContain('원안과 비교');
    expect(compare.querySelectorAll('[data-draft-version]')).toHaveLength(2);
    expect(compare.textContent).toContain('v1 · AI 원안');
    expect(compare.textContent).toContain('원안 대비 변경: 주관');
  });
});
