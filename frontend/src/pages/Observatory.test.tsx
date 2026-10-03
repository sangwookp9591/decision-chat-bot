import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Observatory } from './Observatory';
import { observeApi } from '../api/observe';

vi.mock('../state/events', () => ({ useEventStream: () => ({ status: 'connected', lastSeq: 0 }) }));
vi.mock('../api/observe', async (importOriginal) => ({ ...(await importOriginal<typeof import('../api/observe')>()), observeApi: { requests: vi.fn(), runs: vi.fn(), flow: vi.fn(), playback: vi.fn(), topology: vi.fn(), step: vi.fn() } }));
afterEach(cleanup);
const node = (id: string, name: string, kind = 'code') => ({ id, name, kind, actor_kind: kind, status: 'succeeded' });
beforeEach(() => {
  vi.mocked(observeApi.requests).mockResolvedValue({ items: [{ id: 'req_other', status: 'received' }] });
  vi.mocked(observeApi.runs).mockResolvedValue({ active_run_id: 'run_1', runs: [{ id: 'run_1', status: 'succeeded', versions: {} }] });
  vi.mocked(observeApi.flow).mockResolvedValue({ request_id: 'req_1', run_id: 'run_1', live: false, nodes: [node('s1', '입력 정리'), node('s2', 'Jev 판단', 'ai'), { ...node('review:r', '사람 검토', 'human'), status: 'waiting_human' }], edges: [{ from: 's1', to: 's2', kind: 'sequence' }, { from: 's2', to: 'review:r', kind: 'review' }] });
  vi.mocked(observeApi.playback).mockResolvedValue({ request_id: 'req_1', run_id: 'run_1', live: false, events: [], reviews: [], final_result: 'succeeded' });
});

describe('Observatory deep links and flow (P3-03/P3-04)', () => {
  it('resolves the request from ?run_id= alone and does not fall back to the first request', async () => {
    render(<MemoryRouter initialEntries={['/observatory?run_id=run_1']}><Observatory /></MemoryRouter>);
    await screen.findByRole('list', { name: '실행 순서' });
    await waitFor(() => expect((screen.getByLabelText('요청 선택') as HTMLSelectElement).value).toBe('req_1'));
    expect(observeApi.runs).not.toHaveBeenCalledWith('req_other');
  });
  it('renders steps in the given order with predecessor labels and the edge list', async () => {
    render(<MemoryRouter initialEntries={['/observatory?request_id=req_1']}><Observatory /></MemoryRouter>);
    const list = await screen.findByRole('list', { name: '실행 순서' });
    const names = Array.from(list.querySelectorAll('li.obs-step strong')).map((el) => el.textContent);
    expect(names).toEqual(['입력 정리', 'Jev 판단', '사람 검토']);
    expect(screen.getByText('선행 입력 정리')).toBeInTheDocument();
    const edges = screen.getByRole('list', { name: '실행 관계' });
    expect(Array.from(edges.querySelectorAll('li')).map((li) => li.textContent)).toEqual(['입력 정리 → Jev 판단', 'Jev 판단 → 사람 검토']);
  });
});
