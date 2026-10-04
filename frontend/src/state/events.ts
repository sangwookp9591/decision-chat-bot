import { createElement, useEffect, useRef, useState } from 'react';
import { apiFetch } from '../api/client';
import { eventApi, type EventSnapshot } from '../api/events';

export type StreamFilter = { requestId?: string; enabled?: boolean };
export type StreamEvent = { seq: number; type: string; request_id?: string; run_id?: string; status?: string; step_name?: string; payload?: Record<string, unknown> };
export type StreamStatus = 'connected' | 'reconnecting' | 'disconnected';

/**
 * Every `kind` the server publishes (backend: `append_event*`, `publish_config_in_tx(event_kind=…)`).
 * EventSource only delivers named events to listeners registered for that exact name, so this list must
 * stay equal to the server's kinds; `events.test.ts` greps the backend and fails when they drift.
 * Tenant-wide kinds (`policy.*`, `rule.*`) carry no request id and bypass the request filter.
 */
export const EVENT_KINDS = [
  'request.received', 'run.step', 'judgment.partial', 'judgment.evidence_ready', 'judgment.tasks_ready', 'judgment_saved', 'judgment_failed', 'judgment.cancelled', 'reanalysis.compared',
  'review_decided', 'assignment_created', 'auto_assignment_deferred', 'task.transitioned',
  'policy.published',
  'rule.decision', 'rule.version_created', 'rule.validated', 'rule.publish', 'rule.stop', 'rule.revert',
] as const;
export type EventKind = (typeof EVENT_KINDS)[number];
const isTenantWide = (kind: string) => kind.startsWith('policy.') || kind.startsWith('rule.');

// Cursors are tenant-wide server sequence numbers, so the stored cursor is scoped to tenant + user.
let cursorScope = '';
export function setEventCursorScope(scope: string) { cursorScope = scope; }
const seqKey = () => `jevtriage:last-event-seq:${cursorScope}`;
export function lastEventSeq() { const value = Number(sessionStorage.getItem(seqKey()) || 0); return Number.isFinite(value) && value >= 0 ? value : 0; }
export function acceptEventSeq(seq: number, previous: number) { return Number.isInteger(seq) && seq > previous; }
export const streamUrl = (after: number) => `/api/events/stream?after=${after}`;
export const reconnectDelay = (attempt: number) => Math.min(30000, 1000 * 2 ** attempt);
const MAX_FAILURES = 6;

type StreamCallbacks = { onSnapshot?: (snapshot: EventSnapshot) => void; onEvent?: (event: StreamEvent) => void; onResync?: () => void };

export function useEventStream(filters: StreamFilter = {}, onSnapshot?: (snapshot: EventSnapshot) => void, onEvent?: (event: StreamEvent) => void, onResync?: () => void) {
  const [status, setStatus] = useState<StreamStatus>('reconnecting');
  const [lastSeq, setLastSeq] = useState(lastEventSeq);
  const callbacks = useRef<StreamCallbacks>({ onSnapshot, onEvent, onResync });
  callbacks.current = { onSnapshot, onEvent, onResync };
  useEffect(() => {
    if (filters.enabled === false) return;
    let live = true;
    let current = lastEventSeq();
    let source: EventSource | undefined;
    let timer: number | undefined;
    let failures = 0;
    const remember = (seq: number) => { current = seq; sessionStorage.setItem(seqKey(), String(seq)); setLastSeq(seq); };
    // The browser's own auto-reconnect would add `Last-Event-ID` next to `?after=`, which the server rejects
    // with 400 (and then EventSource gives up). So every error closes the source and we reconnect ourselves.
    const scheduleReconnect = () => {
      if (!live) return;
      if (failures >= MAX_FAILURES) { setStatus('disconnected'); return; }
      setStatus('reconnecting');
      timer = window.setTimeout(connect, reconnectDelay(failures++));
    };
    const recover = (kind: string) => {
      source?.close();
      if (filters.requestId) {
        setStatus('reconnecting');
        void eventApi.snapshot(filters.requestId).then((next) => {
          if (!live) return;
          remember(Math.max(current, next.latest_seq)); callbacks.current.onSnapshot?.(next); callbacks.current.onResync?.(); connect();
        }).catch(() => { if (live) setStatus('disconnected'); });
      } else if (kind === 'snapshot-required' && failures < MAX_FAILURES) {
        // No request to take a snapshot of: drop the stale cursor, let the screen reload, replay from the start.
        failures += 1; remember(0); callbacks.current.onResync?.(); connect();
      } else setStatus('disconnected');
    };
    function connect() {
      if (!live) return;
      const active = new EventSource(streamUrl(current), { withCredentials: true });
      source = active;
      active.onopen = () => { if (!live) return; failures = 0; setStatus('connected'); };
      active.onerror = () => {
        if (!live) return;
        active.close();
        void apiFetch('/api/auth/me').catch(() => undefined); // an expired session surfaces as auth:unauthorized
        scheduleReconnect();
      };
      active.addEventListener('snapshot-required', () => { if (live) recover('snapshot-required'); });
      active.addEventListener('session-expired', () => { if (!live) return; active.close(); setStatus('disconnected'); window.dispatchEvent(new CustomEvent('auth:unauthorized')); });
      EVENT_KINDS.forEach((kind) => active.addEventListener(kind, (event: Event) => {
        if (!live) return;
        const message = event as MessageEvent;
        const seq = Number(message.lastEventId);
        if (!acceptEventSeq(seq, current)) return;
        remember(seq);
        let data: Record<string, unknown> = {};
        try { data = JSON.parse(message.data) as Record<string, unknown>; } catch { return; }
        if (!filters.requestId || data.request_id === filters.requestId || isTenantWide(kind)) {
          callbacks.current.onEvent?.({ seq, type: kind, request_id: data.request_id as string | undefined, run_id: data.run_id as string | undefined, status: data.status as string | undefined, payload: data, ...(typeof data.step_name === 'string' ? { step_name: data.step_name } : {}) });
        }
      }));
    }
    const start = async () => {
      if (filters.requestId) {
        try { const snapshot = await eventApi.snapshot(filters.requestId); if (!live) return; remember(Math.max(current, snapshot.latest_seq)); }
        catch { if (live) setStatus('disconnected'); return; }
      }
      if (live) connect();
    };
    void start();
    return () => { live = false; window.clearTimeout(timer); source?.close(); };
  }, [filters.requestId, filters.enabled]);
  return { status, lastSeq };
}

export function EventConnectionStatus({ status }: { status: StreamStatus }) { const labels = { connected: '실시간 연결됨', reconnecting: '실시간 재연결 중', disconnected: '실시간 연결 끊김' }; return createElement('span', { className: `event-status event-${status}`, role: 'status' }, `● ${labels[status]}`); }
