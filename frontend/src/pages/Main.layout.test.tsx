import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Main } from './Main';
import { requestApi } from '../api/requests';
import { uploadRequest } from './main/uploadRequest';
import type { StreamEvent } from '../state/events';

// CHAT-POLISH: fixed-height conversation, titled request list, summary card in the flow, details in a drawer.
vi.mock('../api/requests', () => ({ requestApi: { detail: vi.fn(), list: vi.fn(), judgment: vi.fn(), runs: vi.fn(), reanalyze: vi.fn(), evidence: vi.fn(), document: vi.fn(), progress: vi.fn() } }));
vi.mock('../api/client', async (original) => ({ ...(await original<typeof import('../api/client')>()), apiFetch: vi.fn() }));
vi.mock('./main/uploadRequest', () => ({ uploadRequest: vi.fn() }));
let emit: (event: Partial<StreamEvent> & { type: string }) => void = () => undefined;
vi.mock('../state/events', () => ({ useEventStream: (_f: unknown, _s: unknown, onEvent: (event: StreamEvent) => void) => { emit = (event) => onEvent({ seq: 1, ...event } as StreamEvent); return { status: 'connected', lastSeq: 0 }; } }));
vi.mock('../state/session', () => ({ useSession: () => ({ user: { id: 'u1', name: 'u1', roles: ['requester'] } }) }));

const classes = { ai_need: '필요', feasibility: '가능', urgency: '일반', lead_org: 'AI팀' };
const judgment = () => ({ id: 'j1', request_id: 'req_0123456789', revision_id: 'rev_1', run_id: 'run_1', classifications: classes, risk_confirmed: false, risks: [], summary: { text: '최종 요약', author: 'x' }, author: 'x', versions: {}, mode: 'live', outputs: [{ id: 'o1', question_id: 'feasibility', type: 'choice', value: '가능', confidence: 0.9, evidence: [{ id: 'ev1', source: 'chat', location: { kind: 'chat' } }] }], draft_tasks: [{ id: 't1', title: '화면 만들기', method: '개발', lead_org: 'IT팀', collab_orgs: [], predecessors: [] }, { id: 't2', title: '모델 학습', method: 'AI', lead_org: 'AI팀', collab_orgs: [], predecessors: [] }, { id: 't3', title: '배포', method: '개발', lead_org: 'IT팀', collab_orgs: [], predecessors: [] }], review_reasons: [], review: null });
const notFound = Object.assign(new Error('not found'), { status: 404 });
const detailOf = (id: string, text: string, status = 'processing') => ({ request: { id, status, revision_number: 1 }, revisions: [{ id: 'rev_1', number: 1, text }], attachments: [] });
const open = (url = '/') => render(<MemoryRouter initialEntries={[url]}><Main /></MemoryRouter>);
const field = () => screen.getByLabelText('요청 내용') as HTMLTextAreaElement;

beforeEach(() => {
  window.matchMedia = vi.fn().mockReturnValue({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }) as never;
  Element.prototype.scrollIntoView = vi.fn() as never;
  vi.mocked(requestApi.list).mockResolvedValue({ items: [] });
  vi.mocked(requestApi.detail).mockResolvedValue(detailOf('req_1', '처음 요청') as never);
  vi.mocked(requestApi.judgment).mockRejectedValue(notFound);
  vi.mocked(requestApi.runs).mockResolvedValue({ active_run_id: 'run_1', runs: [] });
  vi.mocked(requestApi.progress).mockRejectedValue(notFound);
  vi.mocked(uploadRequest).mockResolvedValue({ request_id: 'req_1', status: 'processing', revision: 1 });
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.clearAllMocks(); });

describe('request list rows', () => {
  it('shows the masked first sentence with a status dot and a short id instead of the raw id, under a day heading', async () => {
    const created = new Date(Date.now() - 3 * 60_000).toISOString();
    vi.mocked(requestApi.list).mockResolvedValue({ items: [{ id: 'req_0123456789abcdef', status: 'received', created_at: created }] });
    vi.mocked(requestApi.detail).mockResolvedValue(detailOf('req_0123456789abcdef', '문의 hong@corp.com 로 회신해 주세요. 두 번째 문장입니다.') as never);
    open();
    const row = await screen.findByRole('button', { name: /문의 h\*\*\*@corp\.com 로 회신해 주세요\./ });
    expect(screen.getAllByRole('region', { name: '오늘' }).length).toBeGreaterThan(0); // grouped by day
    expect(row).toHaveTextContent('req_0123');
    expect(row).not.toHaveTextContent('hong@corp.com');
    expect(row).not.toHaveTextContent('두 번째 문장');
    expect(within(row).getByRole('img', { name: /접수|받음|received|분석|대기/ })).toHaveAttribute('data-status'); // small status dot, named for assistive tech
    expect(row.querySelector('.request-title')).not.toBeNull(); // single line, ellipsized by CSS
    expect(row.querySelector('code')).toHaveAttribute('title', 'req_0123456789abcdef');
    expect(row).toHaveTextContent('req_0123456789abcdef'); // the full id stays in the accessible name / text search
  });
  it('groups rows like a chat sidebar: 오늘 / 어제 / 지난 7일', async () => {
    const day = (n: number) => new Date(Date.now() - n * 86_400_000).toISOString();
    vi.mocked(requestApi.list).mockResolvedValue({ items: [{ id: 'req_a', status: 'received', created_at: day(0) }, { id: 'req_b', status: 'received', created_at: day(1) }, { id: 'req_c', status: 'received', created_at: day(4) }] });
    open();
    await screen.findByRole('region', { name: '오늘' });
    expect(screen.getByRole('region', { name: '어제' })).toHaveTextContent('req_b');
    expect(screen.getByRole('region', { name: '지난 7일' })).toHaveTextContent('req_c');
  });
  it('the 새 요청 button on top of the sidebar starts a fresh conversation', async () => {
    open('/?request_id=req_1');
    await screen.findByRole('group', { name: '분석 진행' });
    fireEvent.click(screen.getAllByRole('button', { name: '새 요청' })[0]);
    expect(await screen.findByRole('heading', { name: '안녕하세요, 일동이예요' })).toBeInTheDocument();
  });
  it('the list scrolls on its own: the rows live in one scroll container', async () => {
    vi.mocked(requestApi.list).mockResolvedValue({ items: Array.from({ length: 40 }, (_, i) => ({ id: `req_${i}`, status: 'received' })) });
    open();
    const scroller = (await screen.findByRole('button', { name: /req_39/ })).closest('.list-scroll');
    expect(scroller).not.toBeNull();
    expect(scroller!.querySelectorAll('button')).toHaveLength(40);
  });
  it('below 960px the list opens as a sheet from a top "내 요청" button and closes on pick', async () => {
    vi.mocked(requestApi.list).mockResolvedValue({ items: [{ id: 'req_a', status: 'received' }] });
    open();
    const trigger = screen.getByRole('button', { name: '내 요청' });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    const sheet = await screen.findByRole('dialog', { name: '내 요청 대화' });
    fireEvent.click(await within(sheet).findByRole('button', { name: /req_a/ }));
    expect(screen.queryByRole('dialog', { name: '내 요청 대화' })).toBeNull();
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });
});

describe('result summary card in the conversation', () => {
  async function judged() {
    vi.mocked(requestApi.detail).mockResolvedValue(detailOf('req_1', '처음 요청', 'received') as never);
    vi.mocked(requestApi.judgment).mockResolvedValue(judgment() as never);
    open('/?request_id=req_1');
    return screen.findByRole('group', { name: '일동이의 답변' });
  }
  it('shows the four classifications and a task split summary, not the full detail', async () => {
    const answer = await judged();
    for (const label of ['AI 필요성', '개발 가능성', '긴급도', '주관 조직']) expect(within(answer).getByText(label)).toBeInTheDocument();
    expect(answer).toHaveTextContent('업무 3건');
    expect(answer).toHaveTextContent('IT팀 2');
    expect(answer).toHaveTextContent('AI팀 1');
    expect(within(answer).getByRole('button', { name: '자세히 보기' })).toBeInTheDocument();
    expect(answer.querySelector('.scale-options')).toBeNull();
    expect(within(answer).queryByText('화면 만들기')).toBeNull();
  });
  it('자세히 보기 opens the full result in a drawer; the evidence viewer replaces it and returns to it', async () => {
    vi.mocked(requestApi.document).mockRejectedValue(new Error('x'));
    const answer = await judged();
    fireEvent.click(within(answer).getByRole('button', { name: '자세히 보기' }));
    const drawer = await screen.findByRole('dialog', { name: '판단 상세' });
    expect(within(drawer).getByText('화면 만들기')).toBeInTheDocument();
    expect(drawer.querySelector('.scale-options')).not.toBeNull();
    fireEvent.click(within(drawer).getByRole('button', { name: /근거 열기|근거 패널 열기/ }));
    expect(screen.queryByRole('dialog', { name: '판단 상세' })).toBeNull();
  });
  it('the summary card itself offers evidence so the original text stays one click away', async () => {
    vi.mocked(requestApi.document).mockResolvedValue({ request_id: 'req_1', revision: 1, revision_id: 'rev_1', source: 'chat', kind: 'chat', filename: null, can_read_source: true, units: [] });
    const answer = await judged();
    fireEvent.click(within(answer).getAllByRole('button', { name: /근거 열기|근거 패널 열기/ })[0]);
    await waitFor(() => expect(requestApi.document).toHaveBeenCalled());
  });
});

describe('composer keys', () => {
  it('Enter sends, Shift+Enter keeps a newline, Enter during IME composition does not send', async () => {
    open();
    fireEvent.change(field(), { target: { value: '회의실 예약 화면이 필요해요' } });
    fireEvent.keyDown(field(), { key: 'Enter', shiftKey: true });
    fireEvent.keyDown(field(), { key: 'Enter', isComposing: true });
    fireEvent.keyDown(field(), { key: 'Enter', keyCode: 229 });
    expect(uploadRequest).not.toHaveBeenCalled();
    fireEvent.keyDown(field(), { key: 'Enter' });
    await waitFor(() => expect(uploadRequest).toHaveBeenCalledTimes(1));
    fireEvent.change(field(), { target: { value: '두 번째' } });
    fireEvent.keyDown(field(), { key: 'Enter', metaKey: true });
    await waitFor(() => expect(uploadRequest).toHaveBeenCalledTimes(2));
  });
});

describe('typing indicator and scrolling', () => {
  it('shows three typing dots while the analysis is running and removes them with the result', async () => {
    open('/?request_id=req_1');
    const typing = await screen.findByRole('group', { name: '일동이가 입력 중' });
    expect(typing.querySelectorAll('.typing-dot')).toHaveLength(3);
    vi.mocked(requestApi.judgment).mockResolvedValue(judgment() as never);
    act(() => emit({ type: 'judgment_saved', request_id: 'req_1', payload: { classifications: classes } }));
    await screen.findByRole('group', { name: '일동이의 답변' });
    expect(screen.queryByRole('group', { name: '일동이가 입력 중' })).toBeNull();
  });
  it('while reading above the bottom a new message shows a "새 메시지" pill instead of jumping; the pill scrolls down', async () => {
    open('/?request_id=req_1');
    await screen.findByRole('group', { name: '분석 진행' });
    const scroller = screen.getByRole('log', { name: '일동이와의 대화' }).parentElement as HTMLElement;
    Object.defineProperty(scroller, 'scrollHeight', { configurable: true, value: 2000 });
    Object.defineProperty(scroller, 'clientHeight', { configurable: true, value: 500 });
    scroller.scrollTo = vi.fn() as never;
    scroller.scrollTop = 100; fireEvent.scroll(scroller);
    vi.mocked(requestApi.judgment).mockResolvedValue(judgment() as never);
    act(() => emit({ type: 'judgment_saved', request_id: 'req_1', payload: { classifications: classes } }));
    const pill = await screen.findByRole('button', { name: /새 메시지/ });
    expect(scroller.scrollTo).not.toHaveBeenCalled();
    fireEvent.click(pill);
    expect(scroller.scrollTo).toHaveBeenCalledWith(expect.objectContaining({ top: 2000 }));
    expect(screen.queryByRole('button', { name: /새 메시지/ })).toBeNull();
  });
  it('at the bottom a new message follows smoothly, or instantly under reduced motion', async () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }) as never;
    open('/?request_id=req_1');
    await screen.findByRole('group', { name: '분석 진행' });
    const scroller = screen.getByRole('log', { name: '일동이와의 대화' }).parentElement as HTMLElement;
    Object.defineProperty(scroller, 'scrollHeight', { configurable: true, value: 900 });
    Object.defineProperty(scroller, 'clientHeight', { configurable: true, value: 500 });
    const scrollTo = vi.fn(); scroller.scrollTo = scrollTo as never;
    scroller.scrollTop = 400; fireEvent.scroll(scroller);
    vi.mocked(requestApi.judgment).mockResolvedValue(judgment() as never);
    act(() => emit({ type: 'judgment_saved', request_id: 'req_1', payload: { classifications: classes } }));
    await screen.findByRole('group', { name: '일동이의 답변' });
    await waitFor(() => expect(scrollTo).toHaveBeenCalledWith(expect.objectContaining({ behavior: 'auto' })));
    expect(screen.queryByRole('button', { name: /새 메시지/ })).toBeNull();
  });
});

describe('ChatGPT-style conversation', () => {
  it('empty state: greeting, then the big composer, then the example chips; after the first message the chips and greeting are gone', async () => {
    open();
    const dock = document.querySelector('.composer-dock')!;
    const greeting = screen.getByRole('heading', { name: '안녕하세요, 일동이예요' });
    const chips = screen.getByRole('group', { name: '예시 요청' });
    expect(greeting.compareDocumentPosition(dock) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(dock.compareDocumentPosition(chips) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(document.querySelector('.chat-main')).toHaveAttribute('data-empty');
    expect(screen.getByRole('button', { name: '요청 보내기' })).toBeDisabled(); // nothing typed
    fireEvent.change(field(), { target: { value: '회의실 예약' } });
    expect(screen.getByRole('button', { name: '요청 보내기' })).toBeEnabled();
    fireEvent.keyDown(field(), { key: 'Enter' });
    await screen.findByRole('group', { name: '분석 진행' });
    expect(document.querySelector('.chat-main')).not.toHaveAttribute('data-empty');
    expect(screen.queryByRole('group', { name: '예시 요청' })).toBeNull();
  });
  it('your message is a grey bubble on the right; 일동이 answers without a bubble (fixed avatar column)', async () => {
    vi.mocked(requestApi.judgment).mockResolvedValue(judgment() as never);
    vi.mocked(requestApi.detail).mockResolvedValue(detailOf('req_1', '처음 요청', 'received') as never);
    open('/?request_id=req_1');
    const mine = await screen.findByRole('group', { name: '내가 보낸 요청' });
    expect(mine).toHaveClass('user');
    const answer = await screen.findByRole('group', { name: '일동이의 답변' });
    expect(answer).toHaveClass('assistant');
    expect(answer.querySelector('.chat-avatar')).not.toBeNull();
  });
  it('an action row sits under the answer: copy, re-analyze, source — disabled while provisional, enabled at the final result, same slot', async () => {
    vi.mocked(requestApi.judgment).mockRejectedValue(notFound);
    open('/?request_id=req_1');
    await screen.findByRole('group', { name: '분석 진행' });
    act(() => emit({ type: 'judgment.partial', request_id: 'req_1', payload: { classifications: classes } }));
    const provisional = await screen.findByRole('group', { name: '일동이의 잠정 답변' });
    const row = within(provisional).getByRole('group', { name: '답변 동작' });
    for (const name of ['답변 복사', '다시 분석', '근거 보기']) expect(within(row).getByRole('button', { name })).toBeDisabled();
    const node = provisional;
    vi.mocked(requestApi.judgment).mockResolvedValue(judgment() as never);
    act(() => emit({ type: 'judgment_saved', request_id: 'req_1', payload: { classifications: classes } }));
    const answer = await screen.findByRole('group', { name: '일동이의 답변' });
    expect(answer).toBe(node); // one answer element from the first provisional card on: nothing is re-created or re-animated at the swap
    for (const name of ['답변 복사', '다시 분석', '근거 보기']) expect(within(answer).getByRole('button', { name })).toBeEnabled();
  });
  it('copy puts the summary, the four classifications and the task split on the clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
    vi.mocked(requestApi.judgment).mockResolvedValue(judgment() as never);
    open('/?request_id=req_1');
    const answer = await screen.findByRole('group', { name: '일동이의 답변' });
    fireEvent.click(within(answer).getByRole('button', { name: '답변 복사' }));
    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    const text = writeText.mock.calls[0][0] as string;
    expect(text).toContain('최종 요약'); expect(text).toContain('AI 필요성: 필요'); expect(text).toContain('업무 3건');
    expect(await within(answer).findByRole('button', { name: '복사됨' })).toBeInTheDocument();
  });
  it('the composer grows with its text up to about eight lines', () => {
    open();
    const el = field();
    Object.defineProperty(el, 'scrollHeight', { configurable: true, value: 120 });
    fireEvent.change(el, { target: { value: '여러\n줄\n입력' } });
    expect(el.style.height).toBe('120px');
    Object.defineProperty(el, 'scrollHeight', { configurable: true, value: 900 });
    fireEvent.change(el, { target: { value: `${'줄\n'.repeat(40)}` } });
    expect(parseFloat(el.style.height)).toBeLessThan(900); // capped: beyond ~8 lines it scrolls inside
  });
  it('the send button turns into a stop-shaped, disabled button while the message is on its way', async () => {
    let finish: () => void = () => undefined;
    vi.mocked(uploadRequest).mockImplementation(() => new Promise((resolve) => { finish = () => resolve({ request_id: 'req_1', status: 'processing', revision: 1 }); }));
    open(); fireEvent.change(field(), { target: { value: '챗봇을 도입하고 싶습니다' } });
    fireEvent.click(screen.getByRole('button', { name: '요청 보내기' }));
    const sending = await screen.findByRole('button', { name: '전송 중' });
    expect(sending).toBeDisabled();
    await act(async () => finish());
  });
});
