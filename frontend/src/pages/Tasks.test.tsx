import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Tasks } from './Tasks';
import { taskApi } from '../api/tasks';
import type { StreamEvent } from '../state/events';
let emitTaskEvent: (event: StreamEvent) => void = () => undefined;
vi.mock('../state/events', () => ({ useEventStream: (_f: unknown, _s: unknown, onEvent: (event: StreamEvent) => void) => { emitTaskEvent = onEvent; return { status: 'connected', lastSeq: 0 }; } }));

vi.mock('../api/tasks', () => ({ taskApi: { list: vi.fn(), detail: vi.fn(), transition: vi.fn() } }));
const task = (over: Record<string, unknown> = {}) => ({ id: 'task_1', request_id: 'req_1', title: '데이터 확보', method: 'AI', lead_org: 'AI팀', collab_orgs: [], deliverable: '데이터셋', predecessors: [], predecessor_tasks: [], successors: [], reason: null, block_reasons: [], can_start: true, start_blockers: [], status: '대기', ...over });
afterEach(cleanup);
beforeEach(() => { vi.clearAllMocks(); });
const setup = (t: ReturnType<typeof task>) => { vi.mocked(taskApi.list).mockResolvedValue({ tasks: [t] } as never); vi.mocked(taskApi.detail).mockResolvedValue({ task: t } as never); render(<MemoryRouter><Tasks /></MemoryRouter>); };

describe('Tasks block reasons (P4-01)', () => {
  it('closes task detail on Escape and restores focus to its opener', async () => {
    setup(task()); const opener=await screen.findByRole('button',{name:/데이터 확보/}); opener.focus(); fireEvent.click(opener);
    await screen.findByRole('dialog',{name:'업무 상세'}); fireEvent.keyDown(document,{key:'Escape'});
    await waitFor(()=>expect(screen.queryByRole('dialog',{name:'업무 상세'})).not.toBeInTheDocument());
    expect(opener).toHaveFocus();
  });
  it('refreshes list and selected task when another tab transitions a task', async () => {
    const oldTask = task(); const newTask = task({status:'진행'});
    vi.mocked(taskApi.list).mockResolvedValue({tasks:[oldTask]} as never);
    vi.mocked(taskApi.detail).mockResolvedValue({task:oldTask} as never);
    render(<MemoryRouter><Tasks/></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button',{name:/데이터 확보/}));
    await screen.findByRole('dialog',{name:'업무 상세'});
    vi.mocked(taskApi.list).mockResolvedValue({tasks:[newTask]} as never);
    vi.mocked(taskApi.detail).mockResolvedValue({task:newTask} as never);
    emitTaskEvent({seq:1,type:'task.transitioned',request_id:'req_1',payload:{task_id:'task_1',to:'진행'}});
    await waitFor(()=>expect(screen.getByRole('button',{name:'완료로 변경'})).toBeInTheDocument());
  });
  it('shows Korean block reasons in list and detail and disables the start button', async () => {
    setup(task({ status: '막힘', block_reasons: ['feasibility_unresolved'], can_start: false, start_blockers: ['feasibility_unresolved'] }));
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
  it('translates policy codes in the task premise shown in details', async () => {
    setup(task({ reason: 'risk_clear_max 기준 확인 필요' }));
    fireEvent.click(await screen.findByRole('button', { name: /데이터 확보/ }));
    const dialog = await screen.findByRole('dialog', { name: '업무 상세' });
    expect(dialog).toHaveTextContent('위험 없음 확인 상한 기준 확인 필요');
    expect(dialog).not.toHaveTextContent('risk_clear_max');
  });
  it('keeps the latest block reasons after a 409 and explains them', async () => {
    setup(task({ status: '대기' }));
    fireEvent.click(await screen.findByRole('button', { name: /데이터 확보/ }));
    const latest = task({ status: '막힘', block_reasons: ['feasibility_unresolved'], can_start: false, start_blockers: ['feasibility_unresolved'] });
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
  it('enables start after a completed confirmation, based on the server projection', async () => {
    setup(task({ status: '막힘', block_reasons: ['feasibility_unresolved'], can_start: true, start_blockers: [], predecessor_tasks: [{ id: 'confirm_1', title: '사전 확인', status: '완료', confirmation_task: true }] }));
    fireEvent.click(await screen.findByRole('button', { name: /데이터 확보/ }));
    expect(await screen.findByRole('button', { name: '진행으로 변경' })).toBeEnabled();
  });
});

describe('Tasks empty state and filters', () => {
  it('explains what will appear and what to do next, differently when a filter is active', async () => {
    vi.mocked(taskApi.list).mockResolvedValue({ tasks: [] } as never);
    render(<MemoryRouter><Tasks /></MemoryRouter>);
    expect(await screen.findByText('표시할 배정 업무가 없습니다')).toBeInTheDocument();
    expect(screen.getByText(/팀별 업무가 이곳에 배정됩니다/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('상태'), { target: { value: '막힘' } });
    expect(await screen.findByText(/필터를 풀어/)).toBeInTheDocument();
    expect(taskApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ status: '막힘' }));
  });
});

describe('task row ids (TOSS-SCREENS)',()=>{
 it('shows ids as short chips in the row while keeping the full ids reachable',async()=>{
  const longReq='req_1b6d959edffd4e4e807ea8bc08bc8acd',longTask='tsk_9a8b7c6d5e4f30211234567890abcdef';
  vi.mocked(taskApi.list).mockResolvedValue({tasks:[{id:longTask,request_id:longReq,title:'화면 개발',method:'일반 기술',lead_org:'IT팀',collab_orgs:[],status:'대기',predecessors:[],deliverable:'결과'} as any]} as any);
  const {container}=render(<Tasks/>);const row=await screen.findByRole('button',{name:/화면 개발/});
  expect([...row.querySelectorAll('.short-id [aria-hidden]')].map(x=>x.textContent)).toEqual(['req_…bc8acd','tsk_…abcdef']);
  expect([...container.querySelectorAll('.short-id')].map(x=>x.getAttribute('title'))).toEqual([longReq,longTask]);
 });
});
