import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Evaluation } from './Evaluation';

const mocks = vi.hoisted(() => ({ fetch: vi.fn() }));
vi.mock('../api/client', () => ({ apiFetch: mocks.fetch }));
const labels = { ai_need: '필요', feasibility: '가능', urgency: '일반', team_set: ['AI팀', 'IT팀'], risk_areas: [] as string[] };
const rows = [1, 2, 3].map((n) => ({ id: `sample-${n}`, text: '내용', rationale: '근거', proposed_labels: labels, labels: [], consensus: 'unlabeled' }));
const progress = (total: number) => ({ total, confirmed: 0, deferred: 0, remaining: total, percent: 0 });
const serve = (candidates: object[] = rows) => mocks.fetch.mockImplementation(async (_path: string, init?: RequestInit) => init?.method ? {} : { candidates, progress: progress(candidates.length) });
const open = async () => { render(<MemoryRouter><Evaluation /></MemoryRouter>); await screen.findByRole('heading', { name: /sample-1/ }); };
const putBody = () => JSON.parse((mocks.fetch.mock.calls.find(([, init]) => init?.method === 'PUT')?.[1] as RequestInit).body as string);
const group = (name: string) => screen.queryByRole('radiogroup', { name }) ?? screen.getByRole('group', { name });

afterEach(() => { cleanup(); vi.clearAllMocks(); vi.useRealTimers(); });

describe('Evaluation keyboard workflow', () => {
  it('supports 1-4 field focus, Enter confirmation, and J/K navigation', async () => {
    serve(); await open();
    fireEvent.keyDown(window, { key: '2' });
    expect(document.activeElement).toBe(within(group('개발 가능성')).getByRole('radio', { name: '가능' }));
    fireEvent.keyDown(document.activeElement as Element, { key: 'Enter' });
    await waitFor(() => expect(mocks.fetch).toHaveBeenCalledWith('/api/evaluation/candidates/tuning/sample-1', expect.objectContaining({ method: 'PUT' })));
    fireEvent.keyDown(document.body, { key: 'j' });
    await waitFor(() => expect(screen.queryByRole('heading', { name: /sample-2/ })).not.toBeNull());
    fireEvent.keyDown(document.body, { key: 'k' });
    await waitFor(() => expect(screen.queryByRole('heading', { name: /sample-1/ })).not.toBeNull());
  });

  it('does not steal Enter or letters from the reason textarea or from a focused action button', async () => {
    serve(); await open();
    const reason = screen.getByLabelText('보류 사유');
    reason.focus(); fireEvent.keyDown(reason, { key: 'Enter' }); fireEvent.keyDown(reason, { key: 'j' });
    expect(mocks.fetch.mock.calls.filter(([, init]) => init?.method)).toHaveLength(0);
    expect(screen.queryByRole('heading', { name: /sample-2/ })).toBeNull();
    const defer = screen.getByRole('button', { name: '보류' }); defer.focus(); fireEvent.keyDown(defer, { key: 'Enter' });
    expect(mocks.fetch.mock.calls.filter(([, init]) => init?.method)).toHaveLength(0);
  });

  it('moves the selection with arrow keys inside a radio group', async () => {
    serve(); await open();
    const radios = within(group('AI 필요성')).getAllByRole('radio');
    expect(radios.map((r) => r.textContent?.replace('✓', ''))).toEqual(['필요', '불필요', '혼합', '정보 부족']);
    fireEvent.keyDown(radios[0], { key: 'ArrowRight' });
    expect(radios[1].getAttribute('aria-checked')).toBe('true');
    expect(document.activeElement).toBe(radios[1]);
  });
});

describe('Evaluation answer input (UX-EVAL)', () => {
  it('shows judgments as choice chips, never as JSON text inputs', async () => {
    serve(); await open();
    const textboxes = screen.getAllByRole('textbox');
    expect(textboxes).toHaveLength(1);
    expect(textboxes[0].tagName).toBe('TEXTAREA');
    expect(document.querySelectorAll('input[type="text"], input:not([type])')).toHaveLength(0);
    expect(within(group('AI 필요성')).getByRole('radio', { name: '필요' }).getAttribute('aria-checked')).toBe('true');
    expect(within(group('긴급도')).getByRole('radio', { name: '일반' }).getAttribute('aria-checked')).toBe('true');
    expect(within(group('참여 팀 구성')).getByRole('button', { name: 'AI팀' }).getAttribute('aria-pressed')).toBe('true');
    expect(within(group('참여 팀 구성')).getByRole('button', { name: '현업' }).getAttribute('aria-pressed')).toBe('false');
    const visible = document.body.cloneNode(true) as HTMLElement; visible.querySelectorAll('details').forEach((node) => node.remove());
    expect(visible.textContent).not.toMatch(/\["|\[\]|"필요"/);
  });

  it('saves chip choices in the existing API format (strings and arrays)', async () => {
    serve(); await open();
    fireEvent.click(within(group('AI 필요성')).getByRole('radio', { name: '혼합' }));
    fireEvent.click(within(group('개발 가능성')).getByRole('radio', { name: '정보 부족' }));
    fireEvent.click(within(group('참여 팀 구성')).getByRole('button', { name: 'IT팀' }));
    fireEvent.click(within(group('참여 팀 구성')).getByRole('button', { name: '현업' }));
    fireEvent.click(within(group('위험 영역')).getByRole('button', { name: '규제 검토' }));
    fireEvent.change(screen.getByRole('slider', { name: '확신도' }), { target: { value: '0.5' } });
    expect(screen.getByText('50%')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '확정 (Enter)' }));
    await waitFor(() => expect(putBody()).toBeTruthy());
    expect(putBody()).toEqual({ labels: { ai_need: '혼합', feasibility: '정보 부족', urgency: '일반', team_set: ['AI팀', '현업'], risk_areas: ['규제 검토'] }, confidence: 0.5, status: 'confirmed', reason: null });
    expect((await screen.findByRole('status')).textContent).toContain('라벨을 확정했습니다.');
  });

  it('requires a reason to defer and sends it with the deferred status', async () => {
    serve(); await open();
    fireEvent.click(screen.getByRole('button', { name: '보류' }));
    expect((await screen.findByRole('alert')).textContent).toContain('보류 사유를 입력');
    expect(screen.getByLabelText('보류 사유').getAttribute('aria-invalid')).toBe('true');
    expect(mocks.fetch.mock.calls.filter(([, init]) => init?.method)).toHaveLength(0);
    fireEvent.change(screen.getByLabelText('보류 사유'), { target: { value: '  모호함 ' } });
    fireEvent.click(screen.getByRole('button', { name: '보류' }));
    await waitFor(() => expect(putBody()).toMatchObject({ status: 'deferred', reason: '모호함' }));
  });

  it('final split hides model predictions and blocks confirming until every choice is made', async () => {
    mocks.fetch.mockImplementation(async (path: string) => ({ candidates: path.includes('final') ? rows.map(({ proposed_labels: _p, rationale: _r, ...rest }) => rest) : rows, progress: progress(3) }));
    await open();
    fireEvent.click(screen.getByRole('tab', { name: '최종' }));
    await waitFor(() => expect(screen.getByText('모델 예측 숨김')).toBeTruthy());
    await screen.findByRole('heading', { name: /sample-1/ });
    expect(screen.queryByText('제안 라벨')).toBeNull();
    const confirm = screen.getByRole('button', { name: '확정 (Enter)' }) as HTMLButtonElement;
    expect(confirm.disabled).toBe(true);
    for (const [name, option] of [['AI 필요성', '필요'], ['개발 가능성', '가능'], ['긴급도', '일반']]) fireEvent.click(within(group(name)).getByRole('radio', { name: option }));
    expect(confirm.disabled).toBe(false);
  });
});

describe('Evaluation Korean labels (F6)', () => {
  it('shows consensus state, history and field names in Korean; internal keys only inside 기술 상세', async () => {
    const row = { ...rows[0], consensus: 'consensus_required', my_labels: undefined, labels: [
      { user_id: 'u1', status: 'confirmed', labels, created_at: '2026-10-04T10:00:00Z' },
      { user_id: 'u2', status: 'deferred', labels, reason: '모호', created_at: '2026-10-04T10:05:00Z' }] };
    serve([row]); await open();
    expect(screen.getByText(/검토자 간 의견 불일치/)).toBeTruthy();
    expect(screen.getByText('불일치 · 합의 필요')).toBeTruthy();
    for (const label of ['AI 필요성', '개발 가능성', '긴급도', '참여 팀 구성', '위험 영역']) expect(group(label)).toBeTruthy();
    const history = screen.getAllByRole('listitem');
    expect(history).toHaveLength(2);
    expect(history[0].textContent).toContain('u1'); expect(history[0].textContent).toContain('확정');
    expect(history[1].textContent).toContain('보류 사유: 모호');
    expect(screen.getByRole('button', { name: '합의 라벨 확정' })).toBeTruthy();
    const visible = document.body.cloneNode(true) as HTMLElement; visible.querySelectorAll('details, input, textarea').forEach((node) => node.remove());
    for (const key of ['consensus_required', 'ai_need', 'team_set', 'risk_areas']) expect(visible.textContent).not.toContain(key);
  });

  it.each([['agreed', '일치'], ['unlabeled', '라벨 없음']])('labels the %s state "%s"', async (consensus, text) => {
    serve([{ ...rows[0], consensus }]); await open();
    expect(screen.getByText(text)).toBeTruthy();
  });
});

describe('Evaluation states', () => {
  it('shows an empty state when there are no samples', async () => {
    serve([]); render(<MemoryRouter><Evaluation /></MemoryRouter>);
    expect(await screen.findByText('표본이 없습니다')).toBeTruthy();
  });

  it('explains a missing role instead of showing the form', async () => {
    mocks.fetch.mockRejectedValue({ status: 403, code: 'HTTP_403', message: '권한이 없습니다.' });
    render(<MemoryRouter><Evaluation /></MemoryRouter>);
    expect(await screen.findByText('평가 라벨 권한이 없습니다')).toBeTruthy();
    expect(screen.queryByRole('button', { name: '확정 (Enter)' })).toBeNull();
  });

  it('offers a retry after a load failure', async () => {
    mocks.fetch.mockRejectedValueOnce({ status: 500, code: 'HTTP_500', message: '서버 오류' });
    serve();
    render(<MemoryRouter><Evaluation /></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button', { name: '다시 시도' }));
    expect(await screen.findByRole('heading', { name: /sample-1/ })).toBeTruthy();
  });

  it('keeps the form and shows an error toast when saving fails', async () => {
    mocks.fetch.mockImplementation(async (_path: string, init?: RequestInit) => { if (init?.method) throw { status: 500, code: 'X', message: '저장 실패' }; return { candidates: rows, progress: progress(3) }; });
    await open();
    fireEvent.click(screen.getByRole('button', { name: '확정 (Enter)' }));
    expect((await screen.findByRole('alert')).textContent).toContain('저장 실패');
    expect((screen.getByRole('button', { name: '확정 (Enter)' }) as HTMLButtonElement).disabled).toBe(false);
  });

  it('withholds the skeleton for the first 200ms of loading', async () => {
    vi.useFakeTimers();
    mocks.fetch.mockReturnValue(new Promise(() => undefined));
    render(<MemoryRouter><Evaluation /></MemoryRouter>);
    expect(screen.queryByLabelText('표본을 불러오는 중')).toBeNull();
    await act(async () => { vi.advanceTimersByTime(250); });
    expect(screen.getByLabelText('표본을 불러오는 중')).toBeTruthy();
  });
});
