/**
 * Progressive judgment state (contract: docs/architecture/PROGRESSIVE_RESULTS.md).
 * A pure reducer so every event order can be tested without a browser: optimistic card → request.received →
 * judgment.partial → evidence_ready / tasks_ready (either order) → judgment_saved. State never moves backwards.
 */
export type Classifications = Record<string, unknown>;
export type ProgressStep = { name: string; status: string; kind?: string };
export type ProgressSnapshot = {
  request_id: string; run_id?: string | null; status: string;
  steps?: Array<{ name: string; kind?: string; status: string; started_at?: string | null; ended_at?: string | null }>;
  preliminary?: { classifications?: Classifications; confidences?: Record<string, unknown>; risk_flags?: Record<string, unknown> };
  evidence_ready?: boolean; tasks_ready?: boolean; final?: boolean;
  timings_ms?: { received_to_preliminary?: number; received_to_final?: number };
};
export type ProgressEvent = { type: string; request_id?: string; run_id?: string; step_name?: string; payload?: Record<string, unknown> };
export type ProgressPhase = 'idle' | 'submitting' | 'received' | 'preliminary' | 'final' | 'failed' | 'cancelled';
export type ProgressState = {
  phase: ProgressPhase; requestId: string; runId: string; optimisticText: string; startedAt: number;
  steps: ProgressStep[]; currentStep: string;
  preliminary: { classifications: Classifications; confidences: Record<string, unknown>; risk_flags: Record<string, unknown> } | null;
  finalClassifications: Classifications | null;
  evidenceReady: boolean; evidenceCount?: number; tasksReady: boolean; taskCount?: number;
  failure: string;
};
export type ProgressAction =
  | { type: 'optimistic'; text: string; at: number }
  | { type: 'accepted'; requestId: string }
  | { type: 'rejected'; message: string }
  | { type: 'event'; event: ProgressEvent }
  | { type: 'restore'; progress: ProgressSnapshot }
  | { type: 'reset' };

export const initialProgress: ProgressState = {
  phase: 'idle', requestId: '', runId: '', optimisticText: '', startedAt: 0, steps: [], currentStep: '',
  preliminary: null, finalClassifications: null, evidenceReady: false, tasksReady: false, failure: '',
};
const rank: Record<ProgressPhase, number> = { idle: 0, submitting: 1, received: 2, preliminary: 3, final: 4, failed: 4, cancelled: 4 };
/** A phase only moves forward; `failed` and `final` are terminal. */
const advance = (current: ProgressPhase, next: ProgressPhase): ProgressPhase => (current === 'final' || current === 'failed' || current === 'cancelled' ? current : rank[next] >= rank[current] ? next : current);
const asRecord = (value: unknown): Record<string, unknown> => (value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {});
const upsertStep = (steps: ProgressStep[], step: ProgressStep): ProgressStep[] => steps.some((item) => item.name === step.name) ? steps.map((item) => item.name === step.name ? { ...item, ...step } : item) : [...steps, step];
const FAILED_STATUSES = ['failed', '실패'];

export function progressReducer(state: ProgressState, action: ProgressAction): ProgressState {
  switch (action.type) {
    case 'reset': return initialProgress;
    case 'optimistic': return { ...initialProgress, phase: 'submitting', optimisticText: action.text, startedAt: action.at };
    case 'rejected': return { ...initialProgress, failure: action.message };
    case 'accepted': return state.phase === 'submitting' ? { ...state, phase: 'received', requestId: action.requestId } : state;
    case 'restore': {
      const { progress } = action;
      if (state.requestId && state.requestId !== progress.request_id) return state;
      const steps = (progress.steps || []).map(({ name, kind, status }) => ({ name, status, ...(kind ? { kind } : {}) }));
      const running = [...steps].reverse().find((step) => step.status === 'running') || [...steps].reverse().find((step) => step.status !== 'succeeded');
      const classes = progress.preliminary?.classifications;
      const hasPreliminary = Boolean(classes && Object.keys(classes).length);
      const target: ProgressPhase = progress.status === 'cancelled' ? 'cancelled' : FAILED_STATUSES.includes(progress.status) ? 'failed' : progress.final ? 'final' : hasPreliminary ? 'preliminary' : 'received';
      return {
        ...state, requestId: progress.request_id, runId: progress.run_id || state.runId, phase: advance(state.phase === 'idle' ? 'received' : state.phase, target),
        steps: steps.length > state.steps.length ? steps : state.steps, currentStep: running?.name || state.currentStep,
        preliminary: state.preliminary ?? (hasPreliminary ? { classifications: classes!, confidences: progress.preliminary?.confidences || {}, risk_flags: progress.preliminary?.risk_flags || {} } : null),
        evidenceReady: state.evidenceReady || Boolean(progress.evidence_ready || progress.final), tasksReady: state.tasksReady || Boolean(progress.tasks_ready || progress.final),
      };
    }
    case 'event': {
      const { event } = action; const payload = asRecord(event.payload);
      if (state.requestId && event.request_id && event.request_id !== state.requestId) return state;
      if (state.runId && event.run_id && event.run_id !== state.runId) return state;
      switch (event.type) {
        case 'request.received': return { ...state, requestId: state.requestId || event.request_id || '', phase: advance(state.phase === 'idle' ? 'received' : state.phase, 'received') };
        case 'run.step': {
          if (!event.step_name) return state;
          const status = typeof payload.status === 'string' ? payload.status : 'running';
          return { ...state, steps: upsertStep(state.steps, { name: event.step_name, status }), currentStep: status === 'running' ? event.step_name : state.currentStep || event.step_name };
        }
        case 'judgment.partial': {
          if (state.phase === 'final' || state.phase === 'failed' || state.phase === 'cancelled' || state.preliminary) return state;
          return { ...state, phase: advance(state.phase, 'preliminary'), preliminary: { classifications: asRecord(payload.classifications), confidences: asRecord(payload.confidences), risk_flags: asRecord(payload.risk_flags) } };
        }
        case 'judgment.evidence_ready': return { ...state, evidenceReady: true, evidenceCount: typeof payload.evidence_count === 'number' ? payload.evidence_count : state.evidenceCount };
        case 'judgment.tasks_ready': return { ...state, tasksReady: true, taskCount: typeof payload.task_count === 'number' ? payload.task_count : state.taskCount };
        case 'judgment_saved': {
          const classes = asRecord(payload.classifications);
          return { ...state, phase: 'final', evidenceReady: true, tasksReady: true, finalClassifications: Object.keys(classes).length ? classes : state.finalClassifications };
        }
        case 'judgment_failed': return { ...state, phase: advance(state.phase, 'failed') };
        case 'judgment.cancelled': return { ...state, phase: advance(state.phase, 'cancelled') };
        default: return state;
      }
    }
    default: return state;
  }
}
