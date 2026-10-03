import { apiFetch } from './client';
import { requestApi, type RequestItem } from './requests';

export type FlowNode = {
  id: string; name?: string; kind: string; actor_kind?: string; status: string;
  started_at?: string; ended_at?: string; duration_ms?: number; attempt?: string;
  parent_step_id?: string | null; predecessor_ids?: string[];
  input_summary?: Record<string, unknown>; output_summary?: Record<string, unknown>;
};
export type Flow = { request_id: string; run_id: string; live: boolean; nodes: FlowNode[]; edges: Array<{from:string;to:string;kind:string}> };
export type PlaybackEvent = { type: string; at?: string; step_id?: string; review_id?: string; status?: string; duration_ms?: number };
export type Playback = { request_id: string; run_id: string; live: boolean; events: PlaybackEvent[]; reviews: Array<Record<string, unknown>>; final_result: string };
export type Topology = { request_id: string; kind: string; nodes?: Array<Record<string, unknown>>; edges?: Array<Record<string, unknown>>; services?: Array<Record<string, unknown>> };
export type StepDetail = FlowNode & Record<string, unknown>;
export const observeApi = {
  requests: requestApi.list,
  runs: requestApi.runs,
  flow: (runId: string) => apiFetch<Flow>(`/api/observe/runs/${encodeURIComponent(runId)}/flow`),
  playback: (runId: string) => apiFetch<Playback>(`/api/observe/runs/${encodeURIComponent(runId)}/playback`),
  topology: (requestId: string, kind: 'business'|'service') => apiFetch<Topology>(`/api/observe/requests/${encodeURIComponent(requestId)}/topology?kind=${kind}`),
  step: (stepId: string) => apiFetch<StepDetail>(`/api/observe/steps/${encodeURIComponent(stepId)}`),
};
export type { RequestItem };

export const actorLabels: Record<string,string> = { ai:'AI', code:'코드', rule:'규칙', external:'외부', human:'사람' };

export function playbackPosition(events: PlaybackEvent[], elapsedMs: number, nodeIds: string[]) {
  // Preserve source order for equal timestamps; the explicit index tie-breaker keeps playback
  // deterministic even when a runtime's sort implementation or input timing varies.
  const timestamp = (event: PlaybackEvent) => {
    const parsed = Date.parse(event.at || '');
    return Number.isFinite(parsed) ? parsed : 0;
  };
  const steps = events.map((event, index) => ({ event, index }))
    .filter(({ event }) => event.step_id && (event.type === 'step_started' || event.type === 'step_ended'))
    .sort((a, b) => timestamp(a.event) - timestamp(b.event) || a.index - b.index)
    .map(({ event }) => event);
  const clock = steps[0]?.at ? Date.parse(steps[0].at) + elapsedMs : elapsedMs;
  const active = new Set<string>(); let stopped = false;
  for (const event of steps) {
    if (stopped) continue;
    const at = timestamp(event);
    if (at > clock) continue;
    if (event.type === 'step_started') active.add(event.step_id!);
    if (event.type === 'step_ended') { active.delete(event.step_id!); if (event.status === 'failed') stopped = true; }
  }
  let reached = -1;
  for (const event of steps) {
    if (timestamp(event)>clock) break;
    const index=nodeIds.indexOf(event.step_id!); if(event.type==='step_started'&&index>=0) reached=Math.max(reached,index);
    if(event.type==='step_ended'&&event.status==='failed') break;
  }
  // A review wait is a node of its own (`review:<id>`); once its wait has started the node is reached.
  if (!stopped) for (const event of events) {
    if (event.type !== 'human_wait_started' || !event.review_id || timestamp(event) > clock) continue;
    const index = nodeIds.indexOf(`review:${event.review_id}`); if (index >= 0) reached = Math.max(reached, index);
  }
  const human = events.filter(e=>e.type==='human_wait_started').map(e=>({ id:e.review_id!, compressed:true, actualMs:events.find(x=>x.type==='human_wait_ended'&&x.review_id===e.review_id)?.duration_ms ?? null }));
  return { active, reached, failed: stopped, human };
}
