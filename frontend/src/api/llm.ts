import { apiFetch } from './client';

export type ProviderName = 'anthropic' | 'openai' | 'google';
export type LlmConfig = { provider: ProviderName | null; model: string | null; features: { summary: boolean; task_description: boolean; questions: boolean; rule_explanation: boolean }; timeout_seconds: number; step_budget_seconds: number; max_output_tokens: number };
export const defaultLlmConfig: LlmConfig = { provider: null, model: null, features: { summary: false, task_description: false, questions: false, rule_explanation: false }, timeout_seconds: 15, step_budget_seconds: 20, max_output_tokens: 2000 };
export type ProviderStatus = { provider: ProviderName; key_configured: boolean; sdk_available: boolean; default_model: string };
export type Models = { provider: ProviderName; source: 'api' | 'default'; models: Array<{ id: string; label: string }>; error_code: string | null };
export type ConnectionResult = { provider: ProviderName; model: string; ok: boolean; latency_ms: number; error_code: string | null; message: string; tested_at: string };
export const llmApi = {
  providers: () => apiFetch<{ providers: ProviderStatus[] }>('/api/assist/providers'),
  models: (p: ProviderName) => apiFetch<Models>(`/api/assist/providers/${p}/models`),
  test: (p: ProviderName, model: string) => apiFetch<ConnectionResult>(`/api/assist/providers/${p}/test`, { method: 'POST', body: JSON.stringify({ model }) }),
  explainCandidate: (id: string) => apiFetch<{ candidate_id: string; explanation: string; author: string }>(`/api/learning/candidates/${encodeURIComponent(id)}/explanation`, { method: 'POST' }),
};
