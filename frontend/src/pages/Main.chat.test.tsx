import { AI_NAME } from '../lib/brand';
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { Main } from './Main';
import { requestApi, type Judgment } from '../api/requests';
import { apiFetch } from '../api/client';
import { uploadRequest } from './main/uploadRequest';
import type { StreamEvent } from '../state/events';

// CHAT-1: intake is a conversation with 일동이 — state transitions, file failure choice, info answer → revision, restore.
vi.mock('../api/requests', () => ({ requestApi: { detail: vi.fn(), list: vi.fn(), judgment: vi.fn(), runs: vi.fn(), reanalyze: vi.fn(), evidence: vi.fn(), document: vi.fn(), progress: vi.fn() } }));
vi.mock('../api/client', async (original) => ({ ...(await original<typeof import('../api/client')>()), apiFetch: vi.fn() }));
vi.mock('./main/uploadRequest', () => ({ uploadRequest: vi.fn() }));
let emit: (event: Partial<StreamEvent> & { type: string }) => void = () => undefined;
vi.mock('../state/events', () => ({ useEventStream: (_f: unknown, _s: unknown, onEvent: (event: StreamEvent) => void) => { emit = (event) => onEvent({ seq: 1, ...event } as StreamEvent); return { status: 'connected', lastSeq: 0 }; } }));
vi.mock('../state/session', () => ({ useSession: () => ({ user: { id: 'u1', name: 'u1', roles: ['requester'] } }) }));

const classes = { ai_need: '필요', feasibility: '가능', urgency: '일반', lead_org: 'AI팀' };
const judgment = (extra: Record<string, unknown> = {}, urgency = '일반') => ({ id: 'j1', request_id: 'req_1', revision_id: 'rev_1', run_id: 'run_1', classifications: { ...classes, urgency }, risk_confirmed: false, risks: [], summary: { text: '최종 요약', author: 'x' }, author: 'x', versions: {}, mode: 'live', outputs: [], draft_tasks: [], review_reasons: [], review: null, ...extra }) as unknown as Judgment;
const notFound = Object.assign(new Error('not found'), { status: 404 });
const detail = (status = 'processing', extra: Record<string, unknown> = {}, revisions: unknown[] = [{ id: 'rev_1', number: 1, text: '첫 요청 문장' }], attachments: unknown[] = []) => ({ request: { id: 'req_1', status, revision_number: revisions.length, ...extra }, revisions, attachments });
const Where = () => <div data-testid="where">{useLocation().search}</div>;
const open = (url = '/') => render(<MemoryRouter initialEntries={[url]}><Main /><Where /></MemoryRouter>);
const field = () => screen.getByLabelText('요청 내용') as HTMLTextAreaElement;
const logOf = () => screen.getByRole('log', { name: '일동이와의 대화' });
const mascots = () => Array.from(logOf().querySelectorAll('[data-mascot]')).map((node) => node.getAttribute('data-mascot'));

beforeEach(() => {
  window.matchMedia = vi.fn().mockReturnValue({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }) as never;
  Element.prototype.scrollIntoView = vi.fn() as never;
  vi.mocked(requestApi.list).mockResolvedValue({ items: [] });
  vi.mocked(requestApi.detail).mockResolvedValue(detail() as never);
  vi.mocked(requestApi.judgment).mockRejectedValue(notFound);
  vi.mocked(requestApi.runs).mockResolvedValue({ active_run_id: 'run_1', runs: [] });
  vi.mocked(requestApi.progress).mockRejectedValue(notFound);
  vi.mocked(uploadRequest).mockResolvedValue({ request_id: 'req_1', status: 'processing', revision: 1 });
  vi.mocked(apiFetch).mockResolvedValue({} as never);
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.clearAllMocks(); });

describe('first screen', () => {
  it('greets with the wave mascot, three example requests and a labelled multi-line composer', () => {
    open();
    expect(screen.getByRole('heading', { name: '안녕하세요, 일동이예요' })).toBeInTheDocument();
    expect(mascots()).toContain('wave');
    const examples = within(screen.getByRole('group', { name: '예시 요청' })).getAllByRole('button');
    expect(examples).toHaveLength(3);
    expect(field().tagName).toBe('TEXTAREA');
    expect(screen.getByLabelText('파일 첨부')).toHaveAttribute('type', 'file');
    expect(screen.getByText(/PDF · DOCX · MD, 최대 5개 · 파일당 10 MiB · 합계 25 MiB/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '요청 보내기' })).toBeDisabled();
  });
  it('uses the still PNG instead of the wave video under reduced motion', () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }) as never;
    open();
    expect(document.querySelector('[data-mascot="wave"]')).toHaveAttribute('src', '/assets/mascot/mascot.png');
    expect(document.querySelector('video')).toBeNull();
  });
  it('an example chip fills the composer for editing and sends nothing by itself', () => {
    open();
    const [first] = within(screen.getByRole('group', { name: '예시 요청' })).getAllByRole('button');
    fireEvent.click(first);
    expect(field().value).toBe(first.textContent);
    expect(uploadRequest).not.toHaveBeenCalled();
  });
});

describe('composer', () => {
  it('Enter sends, Shift+Enter only adds a line, Ctrl/⌘+Enter still sends', async () => {
    open();
    fireEvent.change(field(), { target: { value: '회의실 예약 화면이 필요해요' } });
    fireEvent.keyDown(field(), { key: 'Enter', shiftKey: true });
    expect(uploadRequest).not.toHaveBeenCalled();
    fireEvent.keyDown(field(), { key: 'Enter' });
    await waitFor(() => expect(uploadRequest).toHaveBeenCalledTimes(1));
    expect((vi.mocked(uploadRequest).mock.calls[0][0] as FormData).get('text')).toBe('회의실 예약 화면이 필요해요');
    expect(vi.mocked(uploadRequest).mock.calls[0][2]).toBe('/api/requests');
    expect(field().value).toBe(''); // cleared at once: the text now lives in the sent bubble
    fireEvent.change(field(), { target: { value: '두 번째' } });
    fireEvent.keyDown(field(), { key: 'Enter', metaKey: true });
    await waitFor(() => expect(uploadRequest).toHaveBeenCalledTimes(2));
  });
  it('shows attached files as chips, lets you remove one, and caps at five with a notice', () => {
    open();
    const file = (name: string) => new File(['x'], name, { type: 'text/markdown' });
    fireEvent.change(screen.getByLabelText('파일 첨부'), { target: { files: [file('a.md'), file('b.md')] } });
    const chips = screen.getByRole('list', { name: '첨부할 파일' });
    expect(within(chips).getAllByRole('listitem')).toHaveLength(2);
    fireEvent.click(screen.getByRole('button', { name: 'a.md 첨부 제거' }));
    expect(within(chips).getAllByRole('listitem')).toHaveLength(1);
    expect(screen.getByRole('button', { name: '요청 보내기' })).toBeEnabled(); // a file alone is enough
    fireEvent.change(screen.getByLabelText('파일 첨부'), { target: { files: ['c', 'd', 'e', 'f', 'g'].map((n) => file(`${n}.md`)) } });
    expect(within(chips).getAllByRole('listitem')).toHaveLength(5);
    expect(screen.getByRole('status')).toHaveTextContent('최대 5개');
  });
  it('accepts files dropped on the composer', () => {
    open();
    const form = screen.getByRole('form', { name: '일동이에게 요청' });
    fireEvent.drop(form, { dataTransfer: { files: [new File(['x'], 'dropped.pdf', { type: 'application/pdf' })], types: ['Files'] } });
    expect(screen.getByText(/dropped\.pdf/)).toBeInTheDocument();
  });
});

describe('conversation state transitions', () => {
  async function sent(text = '챗봇을 도입하고 싶습니다') {
    open(); fireEvent.change(field(), { target: { value: text } }); fireEvent.click(screen.getByRole('button', { name: '요청 보내기' }));
    await screen.findByRole('group', { name: '분석 진행' });
  }
  it('sent bubble → upload % → analysis steps → provisional card → final result with the like icon', async () => {
    let finish: () => void = () => undefined;
    vi.mocked(uploadRequest).mockImplementation((_form, onProgress) => { onProgress(42); return new Promise((resolve) => { finish = () => resolve({ request_id: 'req_1', status: 'processing', revision: 1 }); }); });
    open(); fireEvent.change(field(), { target: { value: '챗봇을 도입하고 싶습니다' } }); fireEvent.click(screen.getByRole('button', { name: '요청 보내기' }));
    expect(await screen.findByText('42%')).toBeInTheDocument();
    expect(screen.getByRole('group', { name: '내가 보낸 요청' })).toHaveTextContent('챗봇을 도입하고 싶습니다');
    await act(async () => finish());
    await screen.findByRole('group', { name: '분석 진행' });
    expect(screen.getByRole('group', { name: '분석 진행' }).querySelector('[data-mascot="thinking"]')).not.toBeNull();
    act(() => emit({ type: 'run.step', request_id: 'req_1', step_name: `${AI_NAME} 판단`, payload: { status: 'running' } }));
    expect(document.querySelector('.stage-list .current')).toHaveTextContent(`${AI_NAME} 판단`);
    act(() => emit({ type: 'judgment.partial', request_id: 'req_1', payload: { classifications: classes } }));
    expect(screen.getByRole('group', { name: '일동이의 잠정 답변' })).toBeInTheDocument();
    expect(screen.getAllByText('잠정').length).toBeGreaterThanOrEqual(4);
    vi.mocked(requestApi.judgment).mockResolvedValue(judgment());
    act(() => emit({ type: 'judgment_saved', request_id: 'req_1', payload: { classifications: classes } }));
    const answer = await screen.findByRole('group', { name: '일동이의 답변' });
    expect(answer.querySelector('[data-mascot="like"]')).not.toBeNull();
    expect(answer).toHaveTextContent('요청을 정리했어요');
    expect(screen.queryByRole('group', { name: '일동이의 잠정 답변' })).toBeNull();
  });
  it('review-needed results use the surprised icon; urgent results show a warning and no mascot', async () => {
    vi.mocked(requestApi.judgment).mockResolvedValue(judgment({ review: { status: 'pending' } }));
    open('/?request_id=req_1');
    const review = await screen.findByRole('group', { name: '일동이의 답변' });
    expect(review.querySelector('[data-mascot="surprised"]')).not.toBeNull(); expect(review).toHaveTextContent('확인이 조금 필요해요');
    cleanup();
    vi.mocked(requestApi.judgment).mockResolvedValue(judgment({ review: { status: 'pending' } }, '긴급'));
    open('/?request_id=req_1');
    const urgent = await screen.findByRole('group', { name: '일동이의 답변' });
    expect(urgent.querySelector('[data-mascot]')).toBeNull();
    expect(urgent.querySelector('.avatar-warning')).not.toBeNull();
    expect(urgent).toHaveTextContent('긴급 요청이에요. 사람의 확인이 필요해요'); // not colour alone: the text says it
  });
  it('shows the long-wait message after 5 seconds without a result', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await sent();
    expect(screen.queryByText(/조금 더 걸리고 있어요/)).toBeNull();
    await act(async () => { vi.advanceTimersByTime(5100); });
    expect(screen.getByText(/조금 더 걸리고 있어요/)).toBeInTheDocument();
  });
  it('a failed send becomes a cause + retry bubble and returns the draft to the composer', async () => {
    vi.mocked(uploadRequest).mockRejectedValueOnce(new Error('서버에 연결할 수 없습니다.'));
    open(); fireEvent.change(field(), { target: { value: '다시 시도할 요청' } }); fireEvent.click(screen.getByRole('button', { name: '요청 보내기' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('서버에 연결할 수 없습니다.');
    expect(field().value).toBe('다시 시도할 요청');
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    await waitFor(() => expect(uploadRequest).toHaveBeenCalledTimes(2));
  });
  it('keeps review/assignment-like actions disabled until the final judgment is saved', async () => {
    vi.mocked(requestApi.runs).mockResolvedValue({ active_run_id: 'run_1', runs: [] });
    await sent();
    act(() => emit({ type: 'judgment.partial', request_id: 'req_1', payload: { classifications: classes } }));
    expect(screen.getByRole('button', { name: '다시 분석' })).toBeDisabled();
    expect(screen.getByRole('button', { name: /검토·배정은 최종 판단 저장 후/ })).toBeDisabled();
  });
});

describe('questions and choices inside the conversation', () => {
  const failedFile = [{ id: 'att_1', filename: 'broken.pdf', status: 'rejected', reason: 'unsupported_type', revision_id: 'rev_1' }];
  it('file read failure: 일동이 asks, [제외하고 진행] sends the exclusion for the unreadable ids', async () => {
    vi.mocked(requestApi.detail).mockResolvedValue(detail('needs_file_decision', {}, undefined, failedFile) as never);
    open('/?request_id=req_1');
    const bubble = await screen.findByRole('group', { name: '읽기 실패 파일' });
    expect(bubble).toHaveTextContent('이 파일을 읽지 못했어요'); expect(bubble).toHaveTextContent('broken.pdf');
    fireEvent.click(within(bubble).getByRole('button', { name: '제외하고 진행' }));
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith('/api/requests/req_1/file-decision', expect.objectContaining({ method: 'POST', body: JSON.stringify({ exclude: ['att_1'], expected_revision: 1 }) })));
  });
  it('file read failure: [다시 첨부] opens the picker and the next send is a new revision', async () => {
    vi.mocked(requestApi.detail).mockResolvedValue(detail('needs_file_decision', {}, undefined, failedFile) as never);
    open('/?request_id=req_1');
    const picker = screen.getByLabelText('파일 첨부') as HTMLInputElement; const click = vi.spyOn(picker, 'click');
    fireEvent.click(await screen.findByRole('button', { name: '다시 첨부' }));
    expect(click).toHaveBeenCalled();
    fireEvent.change(picker, { target: { files: [new File(['ok'], 'fixed.pdf', { type: 'application/pdf' })] } });
    fireEvent.click(screen.getByRole('button', { name: '다시 첨부해 보내기' }));
    await waitFor(() => expect(uploadRequest).toHaveBeenCalled());
    const [form, , path] = vi.mocked(uploadRequest).mock.calls[0];
    expect(path).toBe('/api/requests/req_1/revisions'); expect((form as FormData).get('expected_revision')).toBe('1');
  });
  it('reviewer info request: 일동이 asks and the answer typed in the same composer becomes a supplement revision', async () => {
    vi.mocked(requestApi.detail).mockResolvedValue(detail('보완 필요', { info_requested: '사용 부서를 알려 주세요', needed_info: JSON.stringify(['사용 부서를 알려 주세요', '완료 희망일']) }) as never);
    vi.mocked(requestApi.judgment).mockResolvedValue(judgment({ review: { status: 'pending' } }));
    open('/?request_id=req_1');
    const ask = await screen.findByRole('group', { name: '보완 요청' });
    expect(ask).toHaveTextContent('사용 부서를 알려 주세요'); expect(ask).toHaveTextContent('완료 희망일');
    fireEvent.click(within(ask).getByRole('button', { name: '답변 입력하기' }));
    expect(field()).toHaveFocus();
    fireEvent.change(field(), { target: { value: '영업기획팀, 다음 달 말까지' } });
    fireEvent.click(screen.getByRole('button', { name: '답변 보내기' }));
    await waitFor(() => expect(uploadRequest).toHaveBeenCalled());
    const [form, , path] = vi.mocked(uploadRequest).mock.calls[0];
    expect(path).toBe('/api/requests/req_1/revisions');
    expect((form as FormData).get('text')).toBe('영업기획팀, 다음 달 말까지'); expect((form as FormData).get('expected_revision')).toBe('1');
    expect(await screen.findByText('영업기획팀, 다음 달 말까지')).toBeInTheDocument(); // optimistic right bubble
  });
  it('after the result: [다시 분석] confirms then calls the reanalysis API; [새 요청 시작] clears the conversation', async () => {
    vi.mocked(requestApi.judgment).mockResolvedValue(judgment());
    vi.mocked(requestApi.reanalyze).mockResolvedValue({ request_id: 'req_1', run_id: 'run_2', job_id: 'j', revision_id: 'rev_1', status: 'processing' });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    open('/?request_id=req_1');
    await screen.findByRole('group', { name: '일동이의 답변' });
    fireEvent.click(screen.getByRole('button', { name: '다시 분석' }));
    await waitFor(() => expect(requestApi.reanalyze).toHaveBeenCalledWith('req_1', 1));
    fireEvent.click(await screen.findByRole('button', { name: '새 요청 시작' }));
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe(''));
    expect(screen.getByRole('heading', { name: '안녕하세요, 일동이예요' })).toBeInTheDocument();
  });
});

describe('restoring a conversation', () => {
  it('rebuilds every revision bubble with its attachment chips from detail, plus the saved result', async () => {
    const revisions = [{ id: 'rev_1', number: 1, text: '처음 요청' }, { id: 'rev_2', number: 2, text: '보완 답변' }];
    const attachments = [{ id: 'att_1', filename: 'spec.pdf', status: 'ok', revision_id: 'rev_1' }, { id: 'att_2', filename: 'notes.md', status: 'ok', revision_id: 'rev_2' }];
    vi.mocked(requestApi.detail).mockResolvedValue(detail('judgment_saved', {}, revisions, attachments) as never);
    vi.mocked(requestApi.judgment).mockResolvedValue(judgment({ revision_id: 'rev_2' }));
    open('/?request_id=req_1');
    const mine = await screen.findAllByRole('group', { name: /내가 보낸 요청|내 보완 답변/ });
    expect(mine).toHaveLength(2);
    expect(mine[0]).toHaveTextContent('처음 요청'); expect(within(mine[0]).getByText('spec.pdf')).toBeInTheDocument();
    expect(mine[1]).toHaveTextContent('보완 답변'); expect(mine[1]).toHaveTextContent('revision 2'); expect(within(mine[1]).getByText('notes.md')).toBeInTheDocument();
    expect(await screen.findByText('최종 요약')).toBeInTheDocument();
    expect(requestApi.detail).toHaveBeenCalledWith('req_1'); expect(requestApi.judgment).toHaveBeenCalledWith('req_1');
  });
  it('restores an in-flight run from the progress API and the list becomes a sheet behind the 내 요청 button', async () => {
    vi.mocked(requestApi.list).mockResolvedValue({ items: [{ id: 'req_1', status: 'processing' }] });
    vi.mocked(requestApi.progress).mockResolvedValue({ request_id: 'req_1', status: 'processing', steps: [{ name: '근거 연결', status: 'running' }], preliminary: { classifications: classes } });
    open('/?request_id=req_1');
    expect(await screen.findByRole('group', { name: '일동이의 잠정 답변' })).toBeInTheDocument();
    const toggle = screen.getByRole('button', { name: '내 요청' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(toggle); expect(toggle).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(await within(await screen.findByRole('dialog', { name: '내 요청 대화' })).findByRole('button', { name: /req_1/ }));
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });
});
