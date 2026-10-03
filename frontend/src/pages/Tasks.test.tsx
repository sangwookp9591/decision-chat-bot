import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Tasks } from './Tasks';
import { taskApi } from '../api/tasks';

vi.mock('../api/tasks', () => ({ taskApi: { list: vi.fn(), detail: vi.fn(), transition: vi.fn() } }));
const task = (over: Record<string, unknown> = {}) => ({ id: 'task_1', request_id: 'req_1', title: '데이터 확보', method: 'AI', lead_org: 'AI팀', collab_orgs: [], deliverable: '데이터셋', predecessors: [], predecessor_tasks: [], successors: [], reason: null, block_reasons: [], status: '대기', ...over });
afterEach(cleanup);
beforeEach(() => { vi.clearAllMocks(); });
const setup = (t: ReturnType<typeof task>) => { vi.mocked(taskApi.list).mockResolvedValue({ tasks: [t] } as never); vi.mocked(taskApi.detail).mockResolvedValue({ task: t } as never); render(<MemoryRouter><Tasks /></MemoryRouter>); };

describe('Tasks block reasons (P4-01)', () => {
  it('shows Korean block reasons in list and detail and disables the start button', async () => {
    setup(task({ status: '막힘', block_reasons: ['feasibility_unresolved'] }));
    const row = await screen.findByRole('button', { name: /데이터 확보/ });
    expect(row.textContent).toContain('개발 가능성');
    expect(row.textContent).not.toContain('feasibility_unresolved');
    fireEvent.click(row);
    const dialog = await screen.findByRole('dialog', { name: '업무 상세' });
    expect(dialog.textContent).toContain('시작 차단 사유');
    expect(dialog.textContent).toContain('개발 가능성');
    expect(dialog.textContent).not.toContain('feasibility_unresolved');
    expect(screen.getByRole('button', { name: '진행으로 변경' })).toBeDisabled();
  });
  it('keeps the latest block reasons after a 409 and explains them', async () => {
    setup(task({ status: '대기' }));
    fireEvent.click(await screen.findByRole('button', { name: /데이터 확보/ }));
    const latest = task({ status: '막힘', block_reasons: ['feasibility_unresolved'] });
    vi.mocked(taskApi.transition).mockRejectedValue({ status: 409, message: 'x' });
    vi.mocked(taskApi.detail).mockResolvedValue({ task: latest } as never);
    fireEvent.click(await screen.findByRole('button', { name: '진행으로 변경' }));
    await waitFor(() => expect(screen.getByRole('button', { name: '진행으로 변경' })).toBeDisabled());
    expect(screen.getByRole('status').textContent).toContain('개발 가능성');
  });
  it('allows starting a waiting task without blockers', async () => {
    setup(task());
    fireEvent.click(await screen.findByRole('button', { name: /데이터 확보/ }));
    expect(await screen.findByRole('button', { name: '진행으로 변경' })).toBeEnabled();
  });
});
