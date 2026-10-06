import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom/vitest';
import { Learning } from './Learning';
import { actionStates, permissions, sampleShortage, suggestRuleId, validationNotice } from './learning/learningModel';

const mocks = vi.hoisted(() => ({ api: {} as Record<string, ReturnType<typeof vi.fn>> }));
vi.mock('../api/learning', async (original) => ({ ...(await original<typeof import('../api/learning')>()), learningApi: mocks.api }));
vi.mock('../api/policy', () => ({ policyApi: { active: vi.fn().mockResolvedValue({ version: 7, config: { learning: { min_effect_sample: 20 } } }), versions: vi.fn().mockResolvedValue({ versions: [] }), version: vi.fn() } }));
vi.mock('../api/graph', () => ({ graphApi: { judgment: vi.fn().mockResolvedValue({ nodes: [], edges: [] }) } }));

const body = { rule_id: 'R-LEAD_ORG-01', version: 1, effect: 'rule', target: 'lead_org', scope: { all: [{ field: 'ai_need', op: 'eq', value: '혼합' }] }, action: { set: 'IT팀' }, candidate_id: 'cand_1' };
const candidate = (status: string, extra = {}) => ({ id: 'cand_1', field: 'lead_org', status, source: 'ai', author: 'code:candidate@v1', support_count: 3, counter_count: 1, created_at: '2026-10-03T00:00:00Z', proposed_body: JSON.stringify(body), uncertainty: JSON.stringify({ support_count: 3, counter_count: 1, minimum_support: 3 }), ...extra });
const detail = (status: string) => ({ ...candidate(status), proposed_body: body, uncertainty: { support_count: 3, counter_count: 1, minimum_support: 3 }, examples: [
  { role: 'support', case: { id: 'cor_1', request_id: 'req_1', run_id: 'run_1', revision_id: 'rev_1', field: 'lead_org', ai_value: 'AI팀', corrected_value: 'IT팀', corrected_by: 'usr_a', corrected_at: '2026-10-02T00:00:00Z', config_version: 3 } },
  { role: 'counter', case: { id: 'rdec_1', request_id: 'req_2', run_id: 'run_2', action: 'approve', actor_id: 'usr_b', created_at: '2026-10-01T00:00:00Z' } }] });
const versionRow = (status: string) => ({ rule_id: 'R-LEAD_ORG-01', versions: [{ version: 1, status, body, config_versions: status === 'validating' ? [] : [8], application_count: 0 }] });

function setup(roles: string[], status = 'approved', versionStatus: string | null = 'validating') {
  Object.assign(mocks.api, {
    orgs: vi.fn().mockResolvedValue({ orgs: [] }),
    candidates: vi.fn().mockResolvedValue([{ ...detail(status), examples: [] }]), candidate: vi.fn().mockResolvedValue(detail(status)),
    corrections: vi.fn().mockResolvedValue({ corrections: [{}, {}, {}, {}] }), generate: vi.fn(),
    rules: vi.fn().mockResolvedValue({ rules: versionStatus ? [{ rule_id: 'R-LEAD_ORG-01', latest_version: 1, version_count: 1 }] : [] }),
    rule: vi.fn().mockResolvedValue(versionRow(versionStatus || 'validating')),
    validations: vi.fn().mockResolvedValue({ validations: [] }), validation: vi.fn(),
    effects: vi.fn().mockRejectedValue({ status: 404, code: 'RULE_NOT_PUBLISHED', message: 'x' }),
  });
  return render(<MemoryRouter><Learning roles={roles} /></MemoryRouter>);
}
beforeEach(() => { cleanup(); sessionStorage.clear(); });
afterEach(cleanup);

describe('learning model', () => {
  it('words insufficient samples without claiming an effect', () => {
    expect(sampleShortage(3, 20)).toBe('표본 부족: 3건 / 최소 20건 — 효과를 확정하지 않습니다.');
    expect(sampleShortage(20, 20)).toBeNull();
    const notes = validationNotice({ sample_count: 42, labeled_count: 19 }, 20);
    expect(notes[0]).toContain('확정이 아닙니다');
    expect(notes[1]).toContain('정답이 있는 표본이 19건');
    expect(validationNotice({ sample_count: 5, labeled_count: 0 }, 20)[1]).toContain('정답 표본이 없어');
  });
  it('gates actions by role and rule state with a reason', () => {
    const ctx = { candidate: null, version: { version: 1, status: 'validating', body, config_versions: [], application_count: 0 }, validationOk: true, revertTargets: 0 } as never;
    const reviewer = actionStates(permissions(['reviewer']), ctx);
    expect(permissions(['reviewer']).canPropose).toBe(true);
    expect(reviewer.publish).toEqual({ enabled: false, reason: '규칙 관리자만 실행할 수 있습니다.' });
    const admin = actionStates(permissions(['rule_admin']), ctx);
    expect(admin.validate.enabled).toBe(true);
    expect(admin.mark_validated.enabled).toBe(true);
    expect(admin.publish).toEqual({ enabled: false, reason: '검증을 완료하지 않은 규칙은 게시할 수 없습니다.' });
    expect(actionStates(permissions(['rule_admin']), { ...(ctx as object), validationOk: false } as never).mark_validated.enabled).toBe(false);
  });
  it('suggests a server-valid rule id that skips used numbers', () => {
    expect(suggestRuleId('lead_org', ['R-LEAD_ORG-01'])).toBe('R-LEAD_ORG-02');
    expect(suggestRuleId('ai_need', [])).toMatch(/^R-[A-Z_]+-[0-9]{2,}$/);
  });
});

describe('Learning page', () => {
  it('requires explicit insufficient-data acknowledgement and a ten-character reason before approval', async () => {
    setup(['rule_admin'], '자료 부족', null);
    mocks.api.decide = vi.fn().mockResolvedValue({ decision_id: 'rdec_ack' });
    mocks.api.createVersion = vi.fn().mockResolvedValue({ version: 1 });
    fireEvent.click(await screen.findByRole('button', { name: /cand_1/ }));
    expect(await screen.findByText('자료 부족 상태임을 확인')).toBeInTheDocument();
    const approve = screen.getByRole('button', { name: '승인' });
    expect(approve).toBeDisabled();
    fireEvent.change(screen.getByLabelText('결정 사유'), { target: { value: '현재 표본이 부족합니다' } });
    expect(approve).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox', { name: '자료 부족 상태임을 확인' }));
    expect(approve).toBeEnabled();
    fireEvent.click(approve);
    await waitFor(() => expect(mocks.api.decide).toHaveBeenCalledWith('cand_1', 'approve', '현재 표본이 부족합니다', undefined, true));
    await waitFor(() => expect(mocks.api.createVersion).toHaveBeenCalledWith('R-LEAD_ORG-01', 'rdec_ack', '현재 표본이 부족합니다', true));
  });

  it('shows the three separated panels, filters and the evidence table with support and counter cases', async () => {
    setup(['rule_admin'], '제안', null);
    expect(await screen.findByText('모델 재학습 없음 · 규칙·컨텍스트로만 반영')).toBeInTheDocument();
    expect(screen.getByText(/수정 기록 4건/)).toBeInTheDocument();
    expect(screen.getByText(/실행에 쓰이지 않음. 후보 1건/)).toBeInTheDocument();
    expect(screen.getByText(/운영 중 0건/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '자료 부족 0' }));
    expect(screen.getByText('표시할 후보가 없습니다.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '검토 필요 1' }));
    fireEvent.click(screen.getByRole('button', { name: /cand_1/ }));
    const table = await screen.findByRole('table', { name: '근거 수정 기록' });
    expect(within(table).getByText('지지')).toBeInTheDocument();
    expect(within(table).getByText('반례')).toBeInTheDocument();
    expect(within(table).getByText(/AI팀 → IT팀/)).toBeInTheDocument();
    expect(screen.getByText(/요청 한 건의 수정 승인은 규칙 게시가 아닙니다/)).toBeInTheDocument();
    expect(screen.getByText(/필수 검토 조건/)).toBeInTheDocument();
  });
  it('disables every action for a reviewer and explains why', async () => {
    setup(['reviewer'], '제안', null);
    fireEvent.click(await screen.findByRole('button', { name: /cand_1/ }));
    await screen.findByLabelText('결정 사유');
    expect(screen.getByRole('button', { name: '승인' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '기각' })).toBeDisabled();
    expect(screen.getAllByText(/규칙 관리자만 실행할 수 있습니다/).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: '게시' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '수정 기록에서 후보 집계' })).toBeEnabled();
  });
  it('keeps publish disabled until validated, and shows insufficient-sample observation after publishing', async () => {
    setup(['rule_admin'], 'approved', 'validating');
    fireEvent.click(await screen.findByRole('button', { name: /cand_1/ }));
    await screen.findByRole('button', { name: '게시' });
    fireEvent.change(screen.getByLabelText('결정 사유'), { target: { value: '검토 완료' } });
    expect(screen.getByRole('button', { name: '게시' })).toBeDisabled();
    expect(screen.getByText(/검증을 완료하지 않은 규칙은 게시할 수 없습니다/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '검증 실행' })).toBeEnabled();
    cleanup();
    const m = (n: number) => ({ sample_count: n, classification_changes: 0, corrections: 0, review_transitions: 0, failures: 0, latency_sample_count: 0, latency_p50_ms: null, latency_p95_ms: null, classification_change_rate: n ? 0 : null, correction_rate: n ? 0 : null, review_transition_rate: n ? 0 : null, failure_rate: n ? 0 : null });
    setup(['rule_admin'], 'approved', 'published');
    mocks.api.effects.mockResolvedValue({ rule_id: 'R-LEAD_ORG-01', active_config_version: 8, published_at: '2026-10-03T00:00:00Z', window_days: 7, minimum_sample: 20, sample_count: 5,
      before_after: { before: m(2), after: m(3), before_from: '', before_to: '', after_from: '', after_to: '' }, groups: { used: m(3), out_of_scope: m(0) }, effect: 'insufficient_sample', shadow_runs_excluded: 0, slo_included: false, comparison_conditions: 'APPLIED used/out_of_scope' });
    fireEvent.click(await screen.findByRole('button', { name: /cand_1/ }));
    await waitFor(() => expect(screen.getByTestId('effect-verdict')).toHaveTextContent('관찰 중 · 표본 부족'));
    expect(screen.getByTestId('used-count')).toHaveTextContent('3');
    expect(screen.getByText(/실제 실행 \/ 규칙 적용·범위 밖 집단 \/ 비교 검증 실행 제외/)).toBeInTheDocument();
    expect(screen.getByText(/비교 검증 실행 0건 제외/)).toBeInTheDocument();
    expect(screen.getByText(/표본 부족: 2건 \/ 최소 20건/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '중단' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('결정 사유'), { target: { value: '중단 사유' } });
    expect(screen.getByRole('button', { name: '중단' })).toBeEnabled();
  });
  it('loads the latest validation from the API after selecting a rule version', async () => {
    setup(['rule_admin']);
    mocks.api.validations.mockResolvedValue({ validations: [{ id: 'val_saved', status: 'completed', side_effects: 0, sample_count: 28, labeled_count: 20 }] });
    fireEvent.click(await screen.findByRole('button', { name: /cand_1/ }));
    await waitFor(() => expect(screen.getByText(/val_saved/)).toBeInTheDocument());
    expect(mocks.api.validations).toHaveBeenCalledWith('R-LEAD_ORG-01', 1);
  });
});

describe('Review rule-learning link', () => {
  it('shows stored original vs corrected values and the single-request notice', async () => {
    const { RuleLearningLink } = await import('./review/RuleLearningLink');
    mocks.api.requestCorrections = vi.fn().mockResolvedValue({ corrections: [{ id: 'cor_1', request_id: 'req_1', field: 'urgency', ai_value: '일반', corrected_value: '긴급', corrected_by: 'usr_a', corrected_at: '2026-10-02T00:00:00Z', revision_id: 'rev_1', run_id: 'run_1', config_version: 2 }] });
    render(<RuleLearningLink requestId="req_1" />);
    const table = await screen.findByRole('table', { name: 'AI 원안과 수정 비교' });
    expect(within(table).getByText('일반')).toBeInTheDocument();
    expect(within(table).getByText('긴급')).toBeInTheDocument();
    expect(screen.getByText(/요청 한 건의 수정 승인은 규칙 게시가 아닙니다/)).toBeInTheDocument();
  });
});

describe('validation inputs (P4-02)', () => {
  it('disables 검증 실행 with a Korean hint when a date is cleared, and never throws', async () => {
    setup(['rule_admin'], 'approved', 'validating');
    fireEvent.click(await screen.findByRole('button', { name: /cand_1/ }));
    const from = await screen.findByLabelText('검증 시작');
    fireEvent.change(from, { target: { value: '' } });
    expect(screen.getByRole('button', { name: '검증 실행' })).toBeDisabled();
    expect(screen.getByText('시작과 끝 날짜를 모두 올바르게 입력해 주세요.')).toBeInTheDocument();
    fireEvent.change(from, { target: { value: '2999-01-01T00:00' } });
    expect(screen.getByText('시작은 끝보다 앞서야 합니다.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '검증 실행' })).toBeDisabled();
  });
});
