import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Monitoring } from './Monitoring';
import { monitoringApi } from '../api/monitoring';

vi.mock('../api/monitoring', () => ({ monitoringApi: { summary: vi.fn(), slo: vi.fn(), failures: vi.fn(), alerts: vi.fn() } }));
const emptyCollection = { complete: true, issues: [], has_collected_events: true, damaged_lines_or_truncations: 0, incomplete_intervals: [], last_collected_at: null, limitations: [] };
const summary = { from: '2026-01-01T00:00:00Z', to: '2026-01-02T00:00:00Z', filters: { org: null, status: null, version: null }, availability: { valid_calls: 4, successful_calls: 4, failed_calls: 0, pending_calls: 0, unknown_validity: 0, ratio: null }, judgment: { eligible_requests: 0, within_120s: 0, failed_120s: 0, pending_120s: 0, ratio: null, late_recoveries: 0, failed_runs: 0 }, requests: { received: 4, failed_before_id: 0 }, cancellations: 0, shadow_runs: 0, latency_ms: { intake_p95: null, text_first_p95: null, attachment_first_p95: null, sse_deliver_p95: null, revision_p95: null, step_p95: null }, steps: {}, review_wait_ms: { p50: null, p95: null, longest: null, unresolved: null }, failures: {}, collection: emptyCollection, unscoped_events: 0 };
afterEach(cleanup);
beforeEach(() => { vi.mocked(monitoringApi.summary).mockResolvedValue(summary); vi.mocked(monitoringApi.slo).mockResolvedValue({ window_start: '', window_end: '', verified: false, reason: '30일 미달', availability: { target: .999, total: 0, failures: 0, remaining_failures: null, burn_rate_1h: null, verified: false }, first_judgment: { target: .99, total: 0, failures: 0, remaining_failures: null, burn_rate_1h: null, verified: false }, collection: emptyCollection }); vi.mocked(monitoringApi.failures).mockResolvedValue({ causes: {}, unscoped_events: 0 }); vi.mocked(monitoringApi.alerts).mockResolvedValue({ alerts: [] }); });
describe('Monitoring', () => {
  it('renders null metrics as 미수집 instead of zero', async () => { render(<MemoryRouter><Monitoring /></MemoryRouter>); expect(await screen.findByText('요청 수')).toBeTruthy(); expect(screen.getAllByText('미수집').length).toBeGreaterThan(0); });
  it('shows an observation incomplete banner', async () => { vi.mocked(monitoringApi.summary).mockResolvedValue({ ...summary, collection: { ...emptyCollection, complete: false, issues: ['collector_stopped'] } }); render(<MemoryRouter><Monitoring /></MemoryRouter>); expect((await screen.findByRole('alert')).textContent).toContain('관측 불완전'); expect(screen.getByText('수집기가 멈춰 있습니다.')).toBeTruthy(); });
  it('uses business assignment and completed review counts and sends organization and status filters', async () => {
    vi.mocked(monitoringApi.summary).mockResolvedValue({ ...summary, business: { request_denominator: 7, org_unconfirmed: 0, auto_assignment_count: 3, review_completed_count: 2 } });
    render(<MemoryRouter><Monitoring /></MemoryRouter>);
    expect((await screen.findAllByText('자동 처리')).length).toBeGreaterThan(0);
    expect(screen.getByText('3')).toBeTruthy(); expect(screen.getByText('2')).toBeTruthy();
    fireEvent.change(screen.getAllByPlaceholderText('조직 ID')[0], { target: { value: 'org-ai' } });
    fireEvent.change(screen.getAllByPlaceholderText('예: review_pending')[0], { target: { value: 'review_pending' } });
    fireEvent.click(screen.getAllByText('적용')[0]);
    await vi.waitFor(() => expect(monitoringApi.summary).toHaveBeenLastCalledWith(expect.objectContaining({ org: 'org-ai', status: 'review_pending' })));
  });
  it('shows a field error instead of throwing when the start date is cleared (P3-09)', async () => {
    const errors: unknown[] = []; const onError = (event: ErrorEvent) => errors.push(event.error); window.addEventListener('error', onError);
    render(<MemoryRouter><Monitoring /></MemoryRouter>); await screen.findByText('요청 수');
    const calls = vi.mocked(monitoringApi.summary).mock.calls.length;
    fireEvent.change(screen.getByLabelText('시작'), { target: { value: '' } });
    expect((await screen.findAllByRole('alert'))[0].textContent).toContain('시작과 종료 시각');
    expect((screen.getByRole('button', { name: '적용' }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: '새로고침' }));
    expect(vi.mocked(monitoringApi.summary).mock.calls.length).toBe(calls + 1);
    fireEvent.change(screen.getByLabelText('시작'), { target: { value: '2999-01-01T00:00' } });
    expect(screen.getAllByRole('alert')[0].textContent).toContain('앞서야');
    window.removeEventListener('error', onError); expect(errors).toEqual([]);
  });
  it('links failures to the supported /observatory route with request and run ids (P3-03)', async () => {
    vi.mocked(monitoringApi.failures).mockResolvedValue({ causes: { storage: [{ ts: '2026-01-01T00:00:00Z', error_class: 'ServiceUnavailable', request_id: 'req_9', run_id: 'run_9', attempt_id: 'att_9' }] }, unscoped_events: 0 } as never);
    render(<MemoryRouter><Monitoring /></MemoryRouter>);
    const link = await screen.findByRole('link', { name: /Trace 보기/ });
    expect(link.getAttribute('href')).toBe('/observatory?request_id=req_9&run_id=run_9');
    expect(screen.getByText(/시도 att_9/)).toBeTruthy();
  });
});

describe('Monitoring internal codes (P4-05)', () => {
  it('translates collection issues, SLO reason and alert kinds; raw codes only inside 자세히', async () => {
    vi.mocked(monitoringApi.summary).mockResolvedValue({ ...summary, collection: { ...emptyCollection, complete: false, issues: ['collector_stopped'] } });
    vi.mocked(monitoringApi.slo).mockResolvedValue({ window_start: '', window_end: '', verified: false, reason: 'Less than 30 days of complete observation', availability: { total: 0, failures: 0, verified: false }, first_judgment: { total: 0, failures: 0, verified: false } } as never);
    vi.mocked(monitoringApi.alerts).mockResolvedValue({ alerts: [{ id: 'a1', kind: 'worker_stopped', ts: '2026-01-01T00:00:00Z', detail: {} }] });
    const { container } = render(<MemoryRouter><Monitoring /></MemoryRouter>);
    await screen.findByText('요청 수');
    const visible = container.cloneNode(true) as HTMLElement; visible.querySelectorAll('details').forEach((node) => node.remove());
    expect(visible.textContent).toContain('수집기가 멈춰 있습니다');
    expect(visible.textContent).toContain('30일에 못 미쳐');
    expect(visible.textContent).toContain('작업자 프로세스가 멈췄습니다');
    expect(visible.textContent).not.toMatch(/collector_stopped|worker_stopped|Less than 30 days/);
  });
});
