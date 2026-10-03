import { createElement, useEffect, useRef, useState } from 'react';
import { eventApi, type EventSnapshot } from '../api/events';

export type StreamFilter = { requestId?: string; enabled?: boolean };
export type StreamEvent = { seq: number; type: string; request_id?: string; run_id?: string; status?: string; step_name?: string };
export type StreamStatus = 'connected' | 'reconnecting' | 'disconnected';
const SEQ_KEY = 'jevtriage:last-event-seq';
export function lastEventSeq() { const value = Number(sessionStorage.getItem(SEQ_KEY) || 0); return Number.isFinite(value) && value >= 0 ? value : 0; }
export function acceptEventSeq(seq: number, previous: number) { return Number.isInteger(seq) && seq > previous; }

export function useEventStream(filters: StreamFilter = {}, onSnapshot?: (snapshot: EventSnapshot) => void, onEvent?: (event: StreamEvent) => void) {
  const [status, setStatus] = useState<StreamStatus>('reconnecting');
  const [lastSeq, setLastSeq] = useState(lastEventSeq);
  const callbacks = useRef({ onSnapshot, onEvent });
  callbacks.current = { onSnapshot, onEvent };
  useEffect(() => {
    if (filters.enabled === false) return;
    let live = true;
    let current = lastEventSeq();
    let source: EventSource | undefined;
    let snapshot: EventSnapshot | undefined;
    const kinds = ['request.updated', 'run.updated', 'run.started', 'run.completed', 'run.step', 'policy.published', 'snapshot-required'];
    const connect = () => {
      if (!live) return;
      const url = `/api/events/stream?after=${current}`;
      source = new EventSource(url, { withCredentials: true });
      const activeSource = source;
      activeSource.onopen = () => live && setStatus('connected');
      activeSource.onerror = () => live && setStatus(activeSource.readyState === EventSource.CLOSED ? 'disconnected' : 'reconnecting');
      kinds.forEach((kind) => activeSource.addEventListener(kind, (event: Event) => {
        if (!live) return;
        if (kind === 'snapshot-required') {
          setStatus('reconnecting');
          if (filters.requestId) void eventApi.snapshot(filters.requestId).then((next) => { if (!live) return; snapshot = next; current = Math.max(current, next.latest_seq); sessionStorage.setItem(SEQ_KEY, String(current)); setLastSeq(current); callbacks.current.onSnapshot?.(next); source?.close(); connect(); }).catch(() => { if (live) setStatus('disconnected'); });
          else { activeSource.close(); setStatus('disconnected'); }
          return;
        }
        const message = event as MessageEvent;
        const seq = Number(message.lastEventId);
        if (!acceptEventSeq(seq, current)) return;
        current = seq;
        sessionStorage.setItem(SEQ_KEY, String(seq));
        setLastSeq(seq);
        let data: Record<string, unknown> = {};
        try { data = JSON.parse(message.data) as Record<string, unknown>; } catch { return; }
        if (!filters.requestId || data.request_id === filters.requestId || kind === 'policy.published') callbacks.current.onEvent?.({ seq, type: kind, request_id: data.request_id as string | undefined, run_id: data.run_id as string | undefined, status: data.status as string | undefined, ...(typeof data.step_name === 'string' ? { step_name: data.step_name } : {}) });
      }));
    };
    const start = async () => {
      if (filters.requestId) {
        try { snapshot = await eventApi.snapshot(filters.requestId); }
        catch { if (live) setStatus('disconnected'); return; }
      }
      if (!live) return;
      current = Math.max(current, snapshot?.latest_seq || 0);
      sessionStorage.setItem(SEQ_KEY, String(current));
      setLastSeq(current);
      connect();
    };
    void start();
    return () => { live = false; source?.close(); };
  }, [filters.requestId]);
  return { status, lastSeq };
}

export function EventConnectionStatus({ status }: { status: StreamStatus }) { const labels = { connected: '실시간 연결됨', reconnecting: '실시간 재연결 중', disconnected: '실시간 연결 끊김' }; return createElement('span', { className: `event-status event-${status}`, role: 'status' }, `● ${labels[status]}`); }
