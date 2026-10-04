import '@testing-library/jest-dom/vitest';
import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Main } from './Main';
import { requestApi } from '../api/requests';
import type { StreamEvent } from '../state/events';

vi.mock('../api/requests', () => ({ requestApi: { detail: vi.fn(), list: vi.fn(), judgment: vi.fn(), runs: vi.fn(), reanalyze: vi.fn(), evidence: vi.fn(), document: vi.fn(), progress: vi.fn() } }));
type Filters = { requestId?: string; enabled?: boolean };
const streams = vi.hoisted(() => new Map<string, (event: unknown) => void>());
vi.mock('../state/events', () => ({
  useEventStream: (filters: Filters, _snapshot: unknown, onEvent: (event: unknown) => void) => { if (filters.enabled !== false) streams.set(filters.requestId ? 'detail' : 'list', onEvent); else streams.delete('detail'); return { status: 'connected', lastSeq: 0 }; },
}));
vi.mock('../state/session', () => ({ useSession: () => ({ user: { id: 'u1', name: 'u1', roles: ['requester'] } }) }));
const notFound = Object.assign(new Error('not found'), { status: 404 });
const emitList = (event: Partial<StreamEvent> & { type: string }) => act(() => streams.get('list')!({ seq: 1, ...event }));

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true }); streams.clear();
  vi.mocked(requestApi.list).mockResolvedValue({ items: [{ id: 'req_old', status: 'received' }] } as never);
  vi.mocked(requestApi.detail).mockResolvedValue({ request: { id: 'req_old', status: 'processing', revision_number: 1 }, revisions: [], attachments: [] } as never);
  vi.mocked(requestApi.judgment).mockRejectedValue(notFound);
  vi.mocked(requestApi.runs).mockResolvedValue({ active_run_id: null, runs: [] });
  vi.mocked(requestApi.progress).mockRejectedValue(notFound);
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.clearAllMocks(); });

// F4 (VERIFY-P7): a tab with no request selected never saw requests created elsewhere.
describe('request list follows tenant events (F4)', () => {
  it('subscribes to tenant events even with no request selected and refetches the list after request.received', async () => {
    render(<MemoryRouter initialEntries={['/']}><Main /></MemoryRouter>);
    expect(await screen.findByText('req_old')).toBeInTheDocument();
    expect(streams.has('list')).toBe(true);
    vi.mocked(requestApi.list).mockResolvedValue({ items: [{ id: 'req_new', status: 'received' }, { id: 'req_old', status: 'received' }] } as never);
    emitList({ type: 'request.received', request_id: 'req_new' });
    await act(async () => { vi.advanceTimersByTime(1000); });
    expect(await screen.findByText('req_new')).toBeInTheDocument();
  });
  it('debounces an event burst into one refetch and keeps the selected detail untouched', async () => {
    render(<MemoryRouter initialEntries={['/?request_id=req_old']}><Main /></MemoryRouter>);
    await screen.findByRole('heading', { name: '분석 진행' });
    const listCalls = vi.mocked(requestApi.list).mock.calls.length; const detailCalls = vi.mocked(requestApi.detail).mock.calls.length;
    for (const type of ['request.received', 'judgment_saved', 'review_decided', 'task.transitioned']) emitList({ type, request_id: 'req_other' });
    await act(async () => { vi.advanceTimersByTime(1500); });
    expect(vi.mocked(requestApi.list).mock.calls.length).toBe(listCalls + 1);
    expect(vi.mocked(requestApi.detail).mock.calls.length).toBe(detailCalls); // events of other requests do not reload the open one
    expect(screen.getByRole('heading', { name: '분석 진행' })).toBeInTheDocument();
  });
});
