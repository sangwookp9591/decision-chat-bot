import '@testing-library/jest-dom/vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Cases } from './Cases';
import { caseApi } from '../api/cases';

vi.mock('../api/cases', async (original) => ({ ...(await original<typeof import('../api/cases')>()), caseApi: { list: vi.fn(), act: vi.fn() } }));
const item = { id: 'case_1', field: 'feasibility', ai_value: '정보 부족', corrected_value: '가능', reason: '사내 API로 가능', situation: 'ERP 연동', request_id: 'req_1', status: 'recorded', conditions: [], exceptions: [], outcome: null, outcome_note: null, version: 1, owner: 'reviewer', consulted: 0, followed: 0, history: [{ version: 1, action: 'recorded', status: 'recorded', by: 'reviewer', at: '2026-10-12T00:00:00Z', conditions: [], exceptions: [], outcome: null, note: null }] };
beforeEach(() => { cleanup(); vi.clearAllMocks(); vi.mocked(caseApi.list).mockResolvedValue({ cases: [item as any] }); vi.mocked(caseApi.act).mockResolvedValue(item as any); });
describe('decision cases', () => {
  it('confirms conditions and exceptions with the current version', async () => {
    render(<Cases />);
    expect(await screen.findByText(/사내 API로 가능/)).toBeTruthy();
    expect(screen.getByRole('button', { name: '조건 확인' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('적용 조건 키워드'), { target: { value: 'ERP, 사내 API' } });
    fireEvent.change(screen.getByLabelText('예외 키워드'), { target: { value: '외부 기관' } });
    fireEvent.click(screen.getByRole('button', { name: '조건 확인' }));
    await waitFor(() => expect(caseApi.act).toHaveBeenCalledWith('case_1', 'confirm', { version: 1, conditions: ['ERP', '사내 API'], exceptions: ['외부 기관'] }));
  });
  it('requires a note before recording an outcome or retiring', async () => {
    render(<Cases />);
    await screen.findByText(/사내 API로 가능/);
    expect(screen.getByRole('button', { name: '폐기' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('결과·폐기 메모'), { target: { value: '배포 후 정상' } });
    fireEvent.click(screen.getByRole('button', { name: '결과 유효' }));
    await waitFor(() => expect(caseApi.act).toHaveBeenCalledWith('case_1', 'outcome', { version: 1, outcome: 'held', note: '배포 후 정상' }));
  });
});
