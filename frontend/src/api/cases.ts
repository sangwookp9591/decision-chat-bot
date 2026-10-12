import { apiFetch } from './client';

export type CaseStatus = 'recorded' | 'confirmed' | 'verified' | 'retired';
export type CaseHistory = { version: number; action: string; status: CaseStatus; by: string; at: string; conditions: string[]; exceptions: string[]; outcome: string | null; outcome_note?: string | null; note: string | null };
export type DecisionCase = { id: string; field: string; ai_value: unknown; corrected_value: unknown; reason: string; situation: string; request_id: string; status: CaseStatus; conditions: string[]; exceptions: string[]; outcome: 'held' | 'failed' | null; outcome_note: string | null; version: number; owner: string; consulted: number; followed: number; created_at?: string; updated_at?: string; history?: CaseHistory[] };
export type Precedent = DecisionCase & { applicability: 'applies' | 'unconfirmed' | 'excepted'; matched_keyword: string | null; age_days: number | null; stale: boolean };
export type PrecedentEntry = { items: Precedent[]; conflict: boolean; hidden_unmet: number };
export type CaseCommand = { version: number; conditions?: string[]; exceptions?: string[]; outcome?: 'held' | 'failed'; note?: string; reason?: string; to_version?: number };

export const caseStatusLabel: Record<CaseStatus, string> = { recorded: '기록됨 · 조건 미확인', confirmed: '조건 확인됨', verified: '결과 검증됨', retired: '폐기' };
export const applicabilityLabel: Record<Precedent['applicability'], string> = { applies: '조건 일치', unconfirmed: '조건 미확인 · 참고만', excepted: '예외 해당 · 적용 금지' };

export const caseApi = {
  list: (status = '') => apiFetch<{ cases: DecisionCase[] }>(`/api/cases${status ? `?status=${encodeURIComponent(status)}` : ''}`),
  act: (id: string, action: 'confirm' | 'outcome' | 'retire' | 'revert', command: CaseCommand) => apiFetch<DecisionCase>(`/api/cases/${encodeURIComponent(id)}/${action}`, { method: 'POST', body: JSON.stringify(command) }),
};
