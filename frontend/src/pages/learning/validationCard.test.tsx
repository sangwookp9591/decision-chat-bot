import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ValidationCard, changeLabel, failureCount } from './sections';
import type { ValidationResult } from '../../api/learning';

afterEach(cleanup);
const result = (over: Partial<ValidationResult> = {}): ValidationResult => ({
  id: 'val_1', rule_version: 'R-1@1', base_config_version: 7, candidate_config_version: '7+R-1@1', from: '2026-10-01T00:00:00Z', to: '2026-10-03T00:00:00Z', scope_filter: null,
  sample_count: 22, labeled_count: 5, changed_count: 8, changes_by_value: { 'lead_org:현업': 8 }, human_correction_needed_base: 3, human_correction_needed_candidate: 1,
  review_transition_base: 0, review_transition_candidate: 0, failures: [], failure_count: 0, side_effects: 0, status: 'completed', max_calls: 10, calls: 0, usage: {}, ...over,
});

describe('validation result display (P3-06)', () => {
  it('shows field/value change counts, the period and the failure count', () => {
    render(<MemoryRouter><ValidationCard result={result()} minimum={20} /></MemoryRouter>);
    expect(screen.getByText(/담당 조직 · 주관 → 현업 8건/)).toBeInTheDocument();
    expect(screen.getByText(/2026.*~.*2026/)).toBeInTheDocument();
    expect(screen.queryByText(/— ~ —/)).toBeNull();
    expect(screen.getByText(/실패 0 · 호출 0\/10/)).toBeInTheDocument();
    expect(screen.queryByText(/^0 \{/)).toBeNull();
  });
  it('formats keys and counts failures from list, number or explicit count', () => {
    expect(changeLabel('ai_need:혼합', 2)).toBe('AI 필요성 → 혼합 2건');
    expect(failureCount({ failures: [{}, {}] })).toBe(2);
    expect(failureCount({ failures: 3 })).toBe(3);
    expect(failureCount({ failures: [], failure_count: 4 })).toBe(4);
  });
});
