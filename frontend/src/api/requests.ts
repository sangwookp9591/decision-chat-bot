import { apiFetch, idempotencyKey } from './client';

export type RequestAttachment = { id: string; filename: string; status: string; reason?: string; byte_count?: number; content_type?: string };
export type RequestDetail = { request: { id: string; status: string; active_run_id?: string | null; revision_number?: number; info_requested?: string | null; needed_info?: string | string[] | null }; revisions: Array<{ id: string; number?: number; revision_number?: number; text?: string }>; attachments: RequestAttachment[]; active_run?: { status?: string } | null };
export type RequestItem = { id: string; status: string; created_at?: string };
export type Evidence = { id: string; source?: 'chat' | 'attachment'; attachment_id?: string | null; location: Record<string, unknown>; source_text?: string; probability?: number };
export type JudgmentOutput = { id: string; question_id: string; type: string; value: unknown; confidence?: number; noul?: unknown; probabilities?: unknown; evidence: Evidence[] };
export type Judgment = { id: string; request_id: string; revision_id: string; run_id: string; classifications: Record<string, unknown>; risk_confirmed: boolean; risks: unknown[]; summary: { text?: string; author?: string } | string; author: string; versions: Record<string, unknown>; mode: 'live' | 'mock'; outputs: JudgmentOutput[]; draft_tasks: Array<Record<string, unknown>>; current_draft_version?: number | null; draft_versions?: Array<{ draft_version: number; source: 'ai' | 'reviewer'; created_by: string; created_at: string | null; tasks: Array<Record<string, unknown>> }>; review_reasons: unknown[]; review: { status: string } | null };
export type RunHistory = { active_run_id?: string | null; runs: Array<{ id: string; revision_id?: string; status: string; versions: Record<string, unknown>; created_at?: string }> };
export type SourceUnit = { unit_id: string; order: number; location: Record<string, unknown>; char_start: number; char_end: number; text?: string };
export type SourceDocument = { request_id: string; revision: number; revision_id: string; source: string; kind: 'pdf' | 'docx' | 'md' | 'chat'; filename: string | null; can_read_source: boolean; units: SourceUnit[] };
export const requestApi = {
  detail: (id: string) => apiFetch<RequestDetail>(`/api/requests/${encodeURIComponent(id)}`),
  list: () => apiFetch<{ items: RequestItem[] }>('/api/requests?limit=50'),
  judgment: (id: string, runId?: string) => apiFetch<Judgment>(`/api/requests/${encodeURIComponent(id)}/judgment${runId ? `?run_id=${encodeURIComponent(runId)}` : ''}`),
  runs: (id: string) => apiFetch<RunHistory>(`/api/requests/${encodeURIComponent(id)}/runs`),
  reanalyze: (id: string, expectedRevision: number, reason?: string) => apiFetch<{ request_id: string; run_id: string; job_id: string; revision_id: string; status: string }>(`/api/requests/${encodeURIComponent(id)}/reanalyze`, { method: 'POST', headers: idempotencyKey(), body: JSON.stringify({ expected_revision: expectedRevision, ...(reason ? { reason } : {}) }) }),
  document: (id: string, revision: string | number, source: string) => apiFetch<SourceDocument>(`/api/requests/${encodeURIComponent(id)}/revisions/${encodeURIComponent(String(revision))}/document?source=${encodeURIComponent(source)}`),
  evidence: (id: string, spanId: string) => apiFetch<Evidence & { source_text?: string }>(`/api/requests/${encodeURIComponent(id)}/evidence/${encodeURIComponent(spanId)}`),
};
