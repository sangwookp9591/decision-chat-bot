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
    expect(document.activeElement).toBe(screen.getByLabelText(/feasibility/));
    fireEvent.keyDown(document.activeElement as Element, { key: 'Enter' });
    await waitFor(() => expect(mocks.fetch).toHaveBeenCalledWith('/api/evaluation/candidates/tuning/sample-1', expect.objectContaining({ method: 'PUT' })));
    fireEvent.keyDown(document.body, { key: 'j' });
    await waitFor(() => expect(screen.queryByText('sample-2')).not.toBeNull());
    fireEvent.keyDown(document.body, { key: 'k' });
    await waitFor(() => expect(screen.queryByText('sample-1')).not.toBeNull());
  });
});
