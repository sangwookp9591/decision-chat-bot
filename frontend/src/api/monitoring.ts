import { apiFetch } from './client';

export type Metric = number | null;
export type MonitoringSummary = {
  from: string; to: string; filters: { org: string | null; status: string | null; version: string | null };
  availability: { valid_calls: number; successful_calls: number; failed_calls: number; pending_calls: number; unknown_validity: number; ratio: Metric; scope_incomplete?: boolean };
  judgment: { eligible_requests: number; within_120s: number; failed_120s: number; pending_120s: number; ratio: Metric; late_recoveries: number; failed_runs: number };
  requests: { received: number; failed_before_id: number };
  cancellations: number; shadow_runs: number;
  business?: { request_denominator: number | null; org_unconfirmed: number | null; auto_assignment_count: number | null; review_completed_count: number | null };
  latency_ms: Record<string, Metric>;
  steps: Record<string, { count: number; p50_ms: Metric; p95_ms: Metric }>;
  review_wait_ms: { p50: Metric; p95: Metric; longest: Metric; unresolved: Metric; source_status?: string };
  failures: Record<string, Array<{ request_id?: string; run_id?: string; attempt_id: string; error_class: string; ts: string }>>;
  collection: CollectionStatus; unscoped_events: number;
};
export type CollectionStatus = { complete: boolean; issues: string[]; has_collected_events: boolean; damaged_lines_or_truncations: number; incomplete_intervals: Array<{ kind: string; start_at: string }>; last_collected_at: string | null; limitations: string[] };
export type Slo = { window_start: string; window_end: string; verified: boolean; reason: string | null; availability: SloMetric; first_judgment: SloMetric; collection: CollectionStatus };
export type SloMetric = { target: number; total: number; failures: number; remaining_failures: Metric; burn_rate_1h: Metric; verified: boolean };
export type Alert = { alerts: Array<Record<string, unknown>> };
const params = (values: Record<string, string>) => { const search = new URLSearchParams(); Object.entries(values).forEach(([k, v]) => { if (v) search.set(k, v); }); return search.toString(); };
export const monitoringApi = {
  summary: (filters: Record<string, string>) => apiFetch<MonitoringSummary>(`/api/monitoring/summary?${params(filters)}`),
  slo: () => apiFetch<Slo>('/api/monitoring/slo'),
  failures: (filters: Record<string, string>) => apiFetch<{ causes: MonitoringSummary['failures']; unscoped_events: number }>(`/api/monitoring/failures?${params(filters)}`),
  alerts: () => apiFetch<Alert>('/api/monitoring/alerts'),
  collection: () => apiFetch<CollectionStatus>('/api/monitoring/collection-status'),
};
