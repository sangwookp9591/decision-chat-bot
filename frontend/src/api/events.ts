import { apiFetch } from './client';
export type EventSnapshot = { request_id: string; status: string; active_run_id?: string | null; latest_seq: number };
export const eventApi = { snapshot: (requestId: string) => apiFetch<EventSnapshot>(`/api/events/snapshot?request_id=${encodeURIComponent(requestId)}`) };
