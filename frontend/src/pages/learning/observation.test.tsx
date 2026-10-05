import '@testing-library/jest-dom/vitest';
import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { Observation } from './sections';
import type { EffectMetrics, RuleEffects } from '../../api/learning';
afterEach(cleanup);
const metrics = (labeled_count: number): EffectMetrics => ({
  sample_count: 40, labeled_count, classification_changes: 0, corrections: 0, review_transitions: 0, failures: 0,
  latency_sample_count: 0, latency_p50_ms: null, latency_p95_ms: null,
  classification_change_rate: 0, correction_rate: 0, review_transition_rate: 0, failure_rate: 0,
});
it('shows all four human label cohorts and leaves insufficient truth unconfirmed', () => {
  const effects: RuleEffects = { rule_id: 'R-AI_NEED-01', active_config_version: 2, published_at: '2026-10-01', window_days: 7, minimum_sample: 20, sample_count: 80,
    before_after: { before: metrics(1), after: metrics(2), before_from: '', before_to: '', after_from: '', after_to: '' },
    groups: { used: metrics(3), out_of_scope: metrics(4) }, effect: 'insufficient_sample', shadow_runs_excluded: 0, slo_included: false, comparison_conditions: '' };
  render(<Observation effects={effects} state="ok" />);
  const row = screen.getByRole('row', { name: '사람 확정 정답 표본 수 1 2 3 4' });
  expect(row).toBeInTheDocument();
  expect(screen.getByText(/미확정: 사람 확정 정답 표본/)).toBeInTheDocument();
  expect(screen.getByText(/정답 정의: 사람이 승인 또는 수정 후 승인한 실행/)).toBeInTheDocument();
});
