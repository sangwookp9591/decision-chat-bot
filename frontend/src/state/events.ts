import { createElement, useEffect, useState } from 'react';
import { eventApi, type EventSnapshot } from '../api/events';

export type StreamFilter = { requestId?: string };
export type StreamEvent = { seq: number; type: string; request_id?: string; run_id?: string; status?: string };
export type StreamStatus = 'connected' | 'reconnecting' | 'disconnected';
const SEQ_KEY = 'jevtriage:last-event-seq';
export function lastEventSeq() { const value = Number(sessionStorage.getItem(SEQ_KEY) || 0); return Number.isFinite(value) && value >= 0 ? value : 0; }
export function acceptEventSeq(seq: number, previous: number) { return Number.isInteger(seq) && seq > previous; }

export function useEventStream(filters: StreamFilter = {}, onSnapshot?: (snapshot: EventSnapshot) => void, onEvent?: (event: StreamEvent) => void) {
  const [status, setStatus] = useState<StreamStatus>('reconnecting');
  const [lastSeq, setLastSeq] = useState(lastEventSeq);
  useEffect(() => {
    let live = true;
    let current = lastEventSeq();
    let source: EventSource;
    const kinds = ['request.updated', 'run.updated', 'run.started', 'run.completed', 'policy.published', 'snapshot-required'];
    const connect = () => {
      if (!live) return;
      const url = `/api/events/stream${current ? `?after=${current}` : ''}`;
      source = new EventSource(url, { withCredentials: true });
      source.onopen = () => live && setStatus('connected');
      source.onerror = () => live && setStatus(source.readyState === EventSource.CLOSED ? 'disconnected' : 'reconnecting');
      kinds.forEach((kind) => source.addEventListener(kind, (event: Event) => {
        if (!live) return;
        if (kind === 'snapshot-required') {
          setStatus('reconnecting');
          if (filters.requestId) void eventApi.snapshot(filters.requestId).then((snapshot) => { if (!live) return; current = Math.max(current, snapshot.latest_seq); sessionStorage.setItem(SEQ_KEY, String(current)); setLastSeq(current); onSnapshot?.(snapshot); source.close(); connect(); }).catch(() => { if (live) setStatus('disconnected'); });
          else { source.close(); setStatus('disconnected'); }
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
        if (!filters.requestId || data.request_id === filters.requestId || kind === 'policy.published') onEvent?.({ seq, type: kind, request_id: data.request_id as string | undefined, run_id: data.run_id as string | undefined, status: data.status as string | undefined });
      }));
    };
    connect();
    return () => { live = false; source.close(); };
  }, [filters.requestId, onEvent, onSnapshot]);
  return { status, lastSeq };
}

export function EventConnectionStatus({ status }: { status: StreamStatus }) { const labels = { connected: '실시간 연결됨', reconnecting: '실시간 재연결 중', disconnected: '실시간 연결 끊김' }; return createElement('span', { className: `event-status event-${status}`, role: 'status' }, `● ${labels[status]}`); }
