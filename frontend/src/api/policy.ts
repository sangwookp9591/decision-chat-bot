import { apiFetch } from './client';

export type PolicyConfig = {
  schema_version: string;
  auto_assign: boolean;
  choice_confidence_thresholds: Record<string, number>;
  noul_probability_thresholds: Record<string, number>;
  risk_clear_max: number;
  reviewer_groups: Record<string, string[]>;
  limits: Record<string, number>;
  evidence_noul_threshold: number;
  catalog_noul_threshold: number;
  feature_flags: Record<string, boolean>;
  rules: Array<Record<string, unknown>>;
};
export type PolicyVersion = { version: number; status: string; reason: string; created_by: string; created_at: string };
export type PolicyDetail = PolicyVersion & { config: PolicyConfig; diff: Record<string, { before: unknown; after: unknown }> };
export type PolicyValidation = { valid: boolean; config: PolicyConfig | null; errors: Array<{ code: string; reason: string }> };
export const policyApi = {
  active: () => apiFetch<{ version: number; config: PolicyConfig }>('/api/policy/active'),
  versions: () => apiFetch<{ versions: PolicyVersion[] }>('/api/policy/versions'),
  version: (version: number) => apiFetch<PolicyDetail>(`/api/policy/versions/${version}`),
  validate: (config: PolicyConfig) => apiFetch<PolicyValidation>('/api/policy/validate', { method: 'POST', body: JSON.stringify({ config }) }),
  publish: (config: PolicyConfig, reason: string, expected_active_version: number) => apiFetch<PolicyDetail>('/api/policy/publish', { method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify({ config, reason, expected_active_version }) }),
  rollback: (target_version: number, reason: string, expected_active_version: number) => apiFetch<PolicyDetail>('/api/policy/rollback', { method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify({ target_version, reason, expected_active_version }) }),
};
