import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Evaluation } from './Evaluation';

const mocks = vi.hoisted(() => ({ fetch: vi.fn() }));
vi.mock('../api/client', () => ({ apiFetch: mocks.fetch }));
const labels = { ai_need: '필요', feasibility: '가능', urgency: '보통', team_set: '플랫폼', risk_areas: [] };
const rows = [1, 2, 3].map((n) => ({ id: `sample-${n}`, text: '내용', rationale: '근거', proposed_labels: labels, labels: [], consensus: 'unlabeled' }));

afterEach(() => { cleanup(); vi.clearAllMocks(); });
describe('Evaluation keyboard workflow', () => {
  it('supports 1-4 field focus, Enter confirmation, and J/K navigation', async () => {
    mocks.fetch.mockResolvedValue({ candidates: rows, progress: { total: 3, confirmed: 0, deferred: 0, remaining: 3, percent: 0 } });
    render(<MemoryRouter><Evaluation /></MemoryRouter>);
    await screen.findByText('sample-1');
    fireEvent.keyDown(window, { key: '2' });
    expect(document.activeElement).toBe(screen.getByLabelText(/개발 가능성/));
    fireEvent.keyDown(document.activeElement as Element, { key: 'Enter' });
    await waitFor(() => expect(mocks.fetch).toHaveBeenCalledWith('/api/evaluation/candidates/tuning/sample-1', expect.objectContaining({ method: 'PUT' })));
    fireEvent.keyDown(document.body, { key: 'j' });
    await waitFor(() => expect(screen.queryByText('sample-2')).not.toBeNull());
    fireEvent.keyDown(document.body, { key: 'k' });
    await waitFor(() => expect(screen.queryByText('sample-1')).not.toBeNull());
  });
});

describe('Evaluation Korean labels (F6)', () => {
  it('shows consensus state and field names in Korean; internal keys only inside 기술 상세', async () => {
    const row = { ...rows[0], consensus: 'consensus_required', labels: [{ user_id: 'u1', status: 'confirmed', labels }, { user_id: 'u2', status: 'deferred', labels, reason: '모호' }] };
    mocks.fetch.mockResolvedValue({ candidates: [row], progress: { total: 1, confirmed: 0, deferred: 0, remaining: 1, percent: 0 } });
    render(<MemoryRouter><Evaluation /></MemoryRouter>);
    await screen.findByText('sample-1');
    expect(screen.getByText(/검토자 간 의견 불일치/)).toBeTruthy();
    for (const label of ['AI 필요성', '개발 가능성', '긴급도', '참여 팀 구성', '위험 영역']) expect(screen.getByLabelText(new RegExp(label))).toBeTruthy();
    const visible = document.body.cloneNode(true) as HTMLElement; visible.querySelectorAll('details, input, textarea').forEach((node) => node.remove());
    for (const key of ['consensus_required', 'ai_need', 'team_set', 'risk_areas']) expect(visible.textContent).not.toContain(key);
    expect(screen.getByText(/확정/, { selector: 'summary' })).toBeTruthy();
  });
});
