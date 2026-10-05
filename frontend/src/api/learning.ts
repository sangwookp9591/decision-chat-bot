import { apiFetch, idempotencyKey } from './client';

export type Predicate = { field?: string; signal?: string; catalog_task?: string; requester_org?: string; op?: string; value?: unknown; present?: boolean };
export type RuleScope = { all: Predicate[] };
export type RuleBody = {
  schema?: string; rule_id: string; version: number; effect: 'rule' | 'context'; target: string;
  scope: RuleScope; action: Record<string, unknown>; context_text?: string; candidate_id?: string; decision_id?: string;
};
export type Uncertainty = { support_count?: number; counter_count?: number; minimum_support?: number; organization_count?: number; single_organization_bias?: boolean; rationale?: string };

/** Candidate row as listed: proposed_body/uncertainty arrive as JSON strings. */
export type CandidateRow = {
  id: string; field: string; status: string; source: 'ai' | 'human' | string; author?: string;
  support_count?: number; counter_count?: number; created_at?: unknown; rationale?: string;
  insufficient_approved?: boolean; insufficient_approval_label?: string | null;
  proposed_body: string | RuleBody; uncertainty?: string | Uncertainty;
};
export type CorrectionCase = {
  id: string; request_id: string; run_id?: string; revision_id?: string; field: string; ai_value?: unknown; corrected_value?: unknown;
  reason?: string; corrected_by?: string; corrected_at?: string; config_version?: number; evidence_span_ids?: string[];
  review_decision_id?: string | null; review_action?: string | null; action?: string;
};
export type CandidateExample = { role: 'support' | 'counter'; case: CorrectionCase & Record<string, unknown> };
export type CandidateDetail = Omit<CandidateRow, 'proposed_body' | 'uncertainty'> & { proposed_body: RuleBody; uncertainty: Uncertainty; examples: CandidateExample[] };

export type RuleVersionRow = { version: number; status: string; body: RuleBody; config_versions: number[]; application_count: number; insufficient_approved?: boolean; insufficient_approval_label?: string | null };
export type RuleDetail = { rule_id: string; versions: RuleVersionRow[] };
export type RuleSummary = { rule_id: string; latest_version: number; version_count: number };

export type ValidationResult = {
  id: string; rule_version: string; base_config_version: number; candidate_config_version: string; from: string; to: string; scope_filter: string | null;
  sample_count: number; labeled_count: number; changed_count: number; changes_by_value: Record<string, number>;
  human_correction_needed_base: number; human_correction_needed_candidate: number;
  review_transition_base: number; review_transition_candidate: number;
  failures: Array<Record<string, unknown>> | number; failure_count?: number; side_effects: number; status: string; max_calls: number; calls: number; usage: Record<string, unknown>;
};
export type EffectMetrics = {
  labeled_count: number; sample_count: number; classification_changes: number; corrections: number; review_transitions: number; failures: number;
  latency_sample_count: number; latency_p50_ms: number | null; latency_p95_ms: number | null;
  classification_change_rate: number | null; correction_rate: number | null; review_transition_rate: number | null; failure_rate: number | null;
};
export type EffectVerdict = 'insufficient_sample' | 'improved' | 'partial' | 'no_change' | 'worse';
export type RuleEffects = {
  rule_id: string; active_config_version: number; published_at: string; window_days: number; minimum_sample: number; sample_count: number;
  before_after: { before: EffectMetrics; after: EffectMetrics; before_from: string; before_to: string; after_from: string; after_to: string };
  groups: { used: EffectMetrics; out_of_scope: EffectMetrics }; effect: EffectVerdict;
  shadow_runs_excluded: number; slo_included: boolean; comparison_conditions: string;
};
export type HumanProposal = { field: string; proposed_action: { set: string }; scope: RuleScope; rationale: string; supporting_correction_ids: string[] };
export type DecisionAction = 'approve' | 'approve_with_scope_change' | 'reject';
export type CorrectionList = { corrections: CorrectionCase[] };

const post = <T>(path: string, body: unknown) => apiFetch<T>(path, { method: 'POST', headers: idempotencyKey(), body: JSON.stringify(body) });
const rule = (id: string) => encodeURIComponent(id);

function parse<T>(value: unknown, fallback: T): T {
  if (typeof value !== 'string') return (value as T) ?? fallback;
  try { return JSON.parse(value) as T; } catch { return fallback; }
}
export function normalizeCandidate(row: CandidateRow): CandidateDetail {
  return { ...row, proposed_body: parse<RuleBody>(row.proposed_body, { rule_id: '', version: 1, effect: 'rule', target: row.field, scope: { all: [] }, action: {} }),
    uncertainty: parse<Uncertainty>(row.uncertainty, {}), examples: [] };
}

export const learningApi = {
  propose: (body: HumanProposal) => post<{ id: string; status: string; source: string }>('/api/learning/candidates', body),
  candidates: async () => (await apiFetch<{ candidates: CandidateRow[] }>('/api/learning/candidates')).candidates.map(normalizeCandidate),
  candidate: async (id: string) => { const row = await apiFetch<CandidateRow & { examples?: CandidateExample[] }>(`/api/learning/candidates/${rule(id)}`); return { ...normalizeCandidate(row), examples: row.examples || [] }; },
  generate: () => apiFetch<{ candidates: unknown[] }>('/api/learning/candidates/generate', { method: 'POST' }),
  corrections: (params: { field?: string; request_id?: string } = {}) => {
    const search = new URLSearchParams(); Object.entries(params).forEach(([k, v]) => v && search.set(k, v));
    return apiFetch<CorrectionList>(`/api/learning/corrections${search.size ? `?${search}` : ''}`);
  },
  requestCorrections: (requestId: string) => apiFetch<CorrectionList>(`/api/requests/${rule(requestId)}/corrections`),
  decide: (candidateId: string, action: DecisionAction, reason: string, scope?: RuleScope, acknowledgeInsufficient = false) =>
    post<{ decision_id: string; candidate_id: string; action: string; confirmed_scope: RuleScope; insufficient_approved?: boolean; insufficient_approval_label?: string | null }>(`/api/learning/candidates/${rule(candidateId)}/decision`, { action, reason, acknowledge_insufficient: acknowledgeInsufficient, ...(scope ? { scope } : {}) }),
  createVersion: (ruleId: string, decisionId: string, reason: string, acknowledgeInsufficient = false) =>
    post<{ rule_id: string; version: number; status: string; body: RuleBody; insufficient_approved?: boolean; insufficient_approval_label?: string | null }>(`/api/learning/rules/${rule(ruleId)}/versions`, { decision_id: decisionId, body: {}, reason, acknowledge_insufficient: acknowledgeInsufficient }),
  rules: () => apiFetch<{ rules: RuleSummary[] }>('/api/learning/rules'),
  rule: (ruleId: string) => apiFetch<RuleDetail>(`/api/learning/rules/${rule(ruleId)}`),
  validate: (ruleId: string, version: number, range: { from: string; to: string; scope_filter?: string; max_calls?: number }) =>
    post<ValidationResult>(`/api/learning/rules/${rule(ruleId)}/versions/${version}/validate`, range),
  validation: (id: string) => apiFetch<ValidationResult>(`/api/learning/validations/${rule(id)}`),
  validations: (ruleId: string, version: number) => apiFetch<{ validations: ValidationResult[] }>(`/api/learning/rules/${rule(ruleId)}/versions/${version}/validations`),
  markValidated: (ruleId: string, version: number, validationId: string, reason: string) =>
    post<{ status: string }>(`/api/learning/rules/${rule(ruleId)}/versions/${version}/mark-validated`, { validation_id: validationId, reason }),
  publish: (ruleId: string, version: number, expected: number, reason: string) =>
    post<{ config_version: number }>(`/api/learning/rules/${rule(ruleId)}/versions/${version}/publish`, { expected_active_config_version: expected, reason }),
  stop: (ruleId: string, expected: number, reason: string) =>
    post<{ config_version: number }>(`/api/learning/rules/${rule(ruleId)}/stop`, { expected_active_config_version: expected, reason }),
  revert: (ruleId: string, toVersion: number, expected: number, reason: string) =>
    post<{ config_version: number }>(`/api/learning/rules/${rule(ruleId)}/revert`, { to_version: toVersion, expected_active_config_version: expected, reason }),
  effects: (ruleId: string, days = 7) => apiFetch<RuleEffects>(`/api/learning/rules/${rule(ruleId)}/effects?days=${days}`),
};
