import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { Monitoring } from './Monitoring';
import { monitoringApi } from '../api/monitoring';

vi.mock('../api/monitoring', () => ({ monitoringApi: { summary: vi.fn(), slo: vi.fn(), failures: vi.fn(), alerts: vi.fn() } }));
const emptyCollection = { complete: true, issues: [], has_collected_events: true, damaged_lines_or_truncations: 0, incomplete_intervals: [], last_collected_at: null, limitations: [] };
const summary = { from: '2026-01-01T00:00:00Z', to: '2026-01-02T00:00:00Z', filters: { org: null, status: null, version: null }, availability: { valid_calls: 4, successful_calls: 4, failed_calls: 0, pending_calls: 0, unknown_validity: 0, ratio: null }, judgment: { eligible_requests: 0, within_120s: 0, failed_120s: 0, pending_120s: 0, ratio: null, late_recoveries: 0, failed_runs: 0 }, requests: { received: 4, failed_before_id: 0 }, cancellations: 0, shadow_runs: 0, latency_ms: { intake_p95: null, text_first_p95: null, attachment_first_p95: null, sse_deliver_p95: null, revision_p95: null, step_p95: null }, steps: {}, review_wait_ms: { p50: null, p95: null, longest: null, unresolved: null }, failures: {}, collection: emptyCollection, unscoped_events: 0 };
beforeEach(() => { vi.mocked(monitoringApi.summary).mockResolvedValue(summary); vi.mocked(monitoringApi.slo).mockResolvedValue({ window_start: '', window_end: '', verified: false, reason: '30일 미달', availability: { target: .999, total: 0, failures: 0, remaining_failures: null, burn_rate_1h: null, verified: false }, first_judgment: { target: .99, total: 0, failures: 0, remaining_failures: null, burn_rate_1h: null, verified: false }, collection: emptyCollection }); vi.mocked(monitoringApi.failures).mockResolvedValue({ causes: {}, unscoped_events: 0 }); vi.mocked(monitoringApi.alerts).mockResolvedValue({ alerts: [] }); });
describe('Monitoring', () => {
  it('renders null metrics as 미수집 instead of zero', async () => { render(<Monitoring />); expect(await screen.findByText('요청 수')).toBeTruthy(); expect(screen.getAllByText('미수집').length).toBeGreaterThan(0); });
  it('shows an observation incomplete banner', async () => { vi.mocked(monitoringApi.summary).mockResolvedValue({ ...summary, collection: { ...emptyCollection, complete: false, issues: ['collector_stopped'] } }); render(<Monitoring />); expect((await screen.findByRole('alert')).textContent).toContain('관측 불완전'); expect(screen.getByText('collector_stopped')).toBeTruthy(); });
  it('uses business assignment and completed review counts and sends organization and status filters', async () => {
    vi.mocked(monitoringApi.summary).mockResolvedValue({ ...summary, business: { request_denominator: 7, org_unconfirmed: 0, auto_assignment_count: 3, review_completed_count: 2 } });
    render(<Monitoring />);
    expect((await screen.findAllByText('자동 처리')).length).toBeGreaterThan(0);
    expect(screen.getByText('3')).toBeTruthy(); expect(screen.getByText('2')).toBeTruthy();
    fireEvent.change(screen.getAllByPlaceholderText('조직 ID')[0], { target: { value: 'org-ai' } });
    fireEvent.change(screen.getAllByPlaceholderText('예: review_pending')[0], { target: { value: 'review_pending' } });
    fireEvent.click(screen.getAllByText('적용')[0]);
    await vi.waitFor(() => expect(monitoringApi.summary).toHaveBeenLastCalledWith(expect.objectContaining({ org: 'org-ai', status: 'review_pending' })));
  });
});
