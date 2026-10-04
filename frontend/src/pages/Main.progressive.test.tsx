import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Main } from './Main';
import { requestApi, type Judgment } from '../api/requests';
import { uploadRequest } from './main/uploadRequest';
import type { StreamEvent } from '../state/events';

vi.mock('../api/requests', () => ({ requestApi: { detail: vi.fn(), list: vi.fn(), judgment: vi.fn(), runs: vi.fn(), reanalyze: vi.fn(), evidence: vi.fn(), document: vi.fn(), progress: vi.fn() } }));
vi.mock('./main/uploadRequest', () => ({ uploadRequest: vi.fn() }));
let emit: (event: Partial<StreamEvent> & { type: string }) => void = () => undefined;
vi.mock('../state/events', () => ({
  useEventStream: (_filters: unknown, _snapshot: unknown, onEvent: (event: StreamEvent) => void) => { emit = (event) => onEvent({ seq: 1, ...event } as StreamEvent); return { status: 'connected', lastSeq: 0 }; },
}));
vi.mock('../state/session', () => ({ useSession: () => ({ user: { id: 'u1', name: 'u1', roles: ['requester'] } }) }));

const classes = { ai_need: '필요', feasibility: '가능', urgency: '일반', lead_org: 'AI팀' };
const judgment = { id: 'j1', request_id: 'req_1', revision_id: 'rev_1', run_id: 'run_1', classifications: { ...classes, feasibility: '조건부 가능' }, risk_confirmed: false, risks: [], summary: { text: '최종 요약', author: 'x' }, author: 'x', versions: {}, mode: 'live', outputs: [], draft_tasks: [], review_reasons: [], review: null } as unknown as Judgment;
const notFound = Object.assign(new Error('not found'), { status: 404 });
const detail = (status = 'processing') => ({ request: { id: 'req_1', status, revision_number: 1 }, revisions: [{ id: 'rev_1', number: 1 }], attachments: [] });
const renderMain = (url = '/') => render(<MemoryRouter initialEntries={[url]}><Main /></MemoryRouter>);

beforeEach(() => {
  vi.mocked(requestApi.list).mockResolvedValue({ items: [] });
  vi.mocked(requestApi.detail).mockResolvedValue(detail() as never);
  vi.mocked(requestApi.judgment).mockRejectedValue(notFound);
  vi.mocked(requestApi.runs).mockResolvedValue({ active_run_id: 'run_1', runs: [] });
  vi.mocked(requestApi.progress).mockRejectedValue(notFound);
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.clearAllMocks(); });

async function submitText(text = '챗봇을 도입하고 싶습니다') {
  fireEvent.change(screen.getByLabelText('요청 내용'), { target: { value: text } });
  fireEvent.click(screen.getByRole('button', { name: '요청 보내기' }));
}

describe('optimistic request card', () => {
  it('shows the submitted request immediately, before the server answers', async () => {
    vi.mocked(uploadRequest).mockReturnValue(new Promise(() => undefined));
    renderMain(); await submitText();
    const card = await screen.findByRole('region', { name: '제출한 요청' });
    expect(card).toHaveTextContent('챗봇을 도입하고 싶습니다');
    expect(card).toHaveTextContent('접수하는 중');
  });
  it('confirms the card with the server request id', async () => {
    vi.mocked(uploadRequest).mockResolvedValue({ request_id: 'req_1', status: 'processing', revision: 1 });
    renderMain(); await submitText();
    expect(await screen.findByRole('region', { name: '제출한 요청' })).toHaveTextContent('req_1');
    expect(screen.getByRole('region', { name: '제출한 요청' })).toHaveTextContent('접수됨');
  });
  it('rolls back on failure: card removed, text kept, reason and retry shown', async () => {
    vi.mocked(uploadRequest).mockRejectedValueOnce(new Error('서버에 연결할 수 없습니다.'));
    renderMain(); await submitText();
    expect(await screen.findByRole('alert')).toHaveTextContent('서버에 연결할 수 없습니다.');
    expect(screen.queryByRole('region', { name: '제출한 요청' })).toBeNull();
    expect(screen.getByLabelText('요청 내용')).toHaveValue('챗봇을 도입하고 싶습니다');
    vi.mocked(uploadRequest).mockResolvedValue({ request_id: 'req_1', status: 'processing', revision: 1 });
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(await screen.findByRole('region', { name: '제출한 요청' })).toHaveTextContent('req_1');
  });
});

describe('partial events render by area', () => {
  async function accepted() {
    vi.mocked(uploadRequest).mockResolvedValue({ request_id: 'req_1', status: 'processing', revision: 1 });
    renderMain(); await submitText(); await screen.findByText(/req_1/);
  }
  it('judgment.partial: four provisional cards at once; evidence and tasks stay skeletons; actions disabled', async () => {
    await accepted();
    act(() => emit({ type: 'judgment.partial', request_id: 'req_1', payload: { classifications: classes, preliminary: true } }));
    const cards = screen.getAllByRole('article').filter((el) => el.classList.contains('judgment-card'));
    expect(cards).toHaveLength(4);
    expect(screen.getAllByText('잠정').length).toBeGreaterThanOrEqual(4);
    expect(screen.getByText(/근거와 업무 분해를 확인하는 중/)).toBeInTheDocument();
    expect(within(cards[0]).getByText('필요')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /검토·배정은 최종 판단 저장 후/ })).toBeDisabled();
    await waitFor(() => expect(document.querySelectorAll('.skeleton').length).toBeGreaterThan(0)); // after the 200ms delay
  });
  it('evidence_ready and tasks_ready fill their own areas (any order)', async () => {
    await accepted();
    act(() => emit({ type: 'judgment.tasks_ready', request_id: 'req_1', payload: { task_count: 3 } }));
    act(() => emit({ type: 'judgment.partial', request_id: 'req_1', payload: { classifications: classes } }));
    expect(screen.getByText('업무 3건 준비됨')).toBeInTheDocument();
    expect(screen.queryByText(/근거 \d+건 연결됨/)).toBeNull();
    act(() => emit({ type: 'judgment.evidence_ready', request_id: 'req_1', payload: { evidence_count: 5 } }));
    expect(screen.getByText('근거 5건 연결됨')).toBeInTheDocument();
  });
  it('judgment_saved updates the cards from the event payload before the detail call returns', async () => {
    await accepted();
    let release: (value: Judgment) => void = () => undefined;
    vi.mocked(requestApi.judgment).mockReturnValue(new Promise((resolve) => { release = resolve; }));
    act(() => emit({ type: 'judgment.partial', request_id: 'req_1', payload: { classifications: classes } }));
    act(() => emit({ type: 'judgment_saved', request_id: 'req_1', payload: { classifications: { ...classes, feasibility: '조건부 가능' } } }));
    expect(screen.queryByText('잠정')).toBeNull();
    expect(screen.getAllByText('조건부 가능').length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: /검토·배정은 최종 판단 저장 후/ })).toBeNull();
    await act(async () => release(judgment));
    expect(await screen.findByText('최종 요약')).toBeInTheDocument();
  });
  it('ignores events of another request', async () => {
    await accepted();
    act(() => emit({ type: 'judgment.partial', request_id: 'other', payload: { classifications: classes } }));
    expect(screen.queryByText('잠정')).toBeNull();
  });
});

describe('reload restores from the progress API', () => {
  it('rebuilds the provisional cards and current step without events', async () => {
    vi.mocked(requestApi.progress).mockResolvedValue({ request_id: 'req_1', run_id: 'run_1', status: 'processing', steps: [{ name: 'Jev 판단', kind: 'ai', status: 'succeeded' }, { name: '근거 연결', kind: 'ai', status: 'running' }], preliminary: { classifications: classes }, evidence_ready: false, tasks_ready: false, final: false });
    renderMain('/?request_id=req_1');
    expect(await screen.findAllByText('잠정')).not.toHaveLength(0);
    expect(requestApi.progress).toHaveBeenCalledWith('req_1');
    expect(document.querySelector('.stage-list .current')).toHaveTextContent('근거 연결');
  });
});

describe('slow and failed runs', () => {
  it('after 5s without a final result shows the long-wait notice with the current step', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(requestApi.progress).mockResolvedValue({ request_id: 'req_1', status: 'processing', steps: [{ name: '근거 연결', status: 'running' }] });
    renderMain('/?request_id=req_1');
    await screen.findByRole('heading', { name: '분석 진행' });
    expect(screen.queryByText(/평소보다 오래 걸리고 있어요/)).toBeNull();
    await act(async () => { vi.advanceTimersByTime(5100); });
    expect(screen.getByText(/평소보다 오래 걸리고 있어요/)).toHaveTextContent('근거 연결');
  });
  it('judgment_failed shows the cause at once with a retry button', async () => {
    vi.mocked(uploadRequest).mockResolvedValue({ request_id: 'req_1', status: 'processing', revision: 1 });
    renderMain(); await submitText(); await screen.findByText(/req_1/);
    vi.mocked(requestApi.detail).mockResolvedValue(detail('failed') as never);
    act(() => emit({ type: 'judgment_failed', request_id: 'req_1', payload: {} }));
    expect(await screen.findByRole('alert')).toHaveTextContent('분석 실행이 실패했습니다');
    expect(screen.getByRole('button', { name: '다시 시도' })).toBeInTheDocument();
  });
});
