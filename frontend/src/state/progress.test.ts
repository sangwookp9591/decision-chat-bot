import { describe, expect, it } from 'vitest';
import { initialProgress, progressReducer, type ProgressAction, type ProgressState } from './progress';

const run = (actions: ProgressAction[], from: ProgressState = initialProgress) => actions.reduce(progressReducer, from);
const partial: ProgressAction = { type: 'event', event: { type: 'judgment.partial', request_id: 'r1', payload: { classifications: { ai_need: '필요', feasibility: '가능', urgency: '일반', lead_org: 'AI팀' }, confidences: { ai_need: 0.8 }, preliminary: true } } };
const evidence: ProgressAction = { type: 'event', event: { type: 'judgment.evidence_ready', request_id: 'r1', payload: { evidence_count: 4 } } };
const tasks: ProgressAction = { type: 'event', event: { type: 'judgment.tasks_ready', request_id: 'r1', payload: { task_count: 3 } } };
const saved: ProgressAction = { type: 'event', event: { type: 'judgment_saved', request_id: 'r1', payload: { classifications: { ai_need: '필요', feasibility: '조건부 가능', urgency: '일반', lead_org: 'AI팀' } } } };
const submitted = (): ProgressState => run([{ type: 'optimistic', text: '챗봇 도입 요청', at: 1000 }, { type: 'accepted', requestId: 'r1' }]);

describe('optimistic request card', () => {
  it('shows the submitted request at once and confirms with the server id', () => {
    const pending = run([{ type: 'optimistic', text: '챗봇 도입 요청', at: 1000 }]);
    expect(pending).toMatchObject({ phase: 'submitting', optimisticText: '챗봇 도입 요청', requestId: '' });
    expect(progressReducer(pending, { type: 'accepted', requestId: 'r1' })).toMatchObject({ phase: 'received', requestId: 'r1', optimisticText: '챗봇 도입 요청', startedAt: 1000 });
  });
  it('rolls the card back on failure and keeps the reason', () => {
    const failed = run([{ type: 'optimistic', text: 'x', at: 1 }, { type: 'rejected', message: '서버에 연결할 수 없습니다.' }]);
    expect(failed).toMatchObject({ phase: 'idle', optimisticText: '', failure: '서버에 연결할 수 없습니다.' });
  });
});

describe('event order', () => {
  it('partial shows provisional classifications; evidence and tasks fill their own areas', () => {
    const afterPartial = run([partial], submitted());
    expect(afterPartial).toMatchObject({ phase: 'preliminary', evidenceReady: false, tasksReady: false });
    expect(afterPartial.preliminary?.classifications.ai_need).toBe('필요');
    expect(run([evidence], afterPartial)).toMatchObject({ evidenceReady: true, evidenceCount: 4, tasksReady: false });
    expect(run([evidence, tasks], afterPartial)).toMatchObject({ evidenceReady: true, tasksReady: true, taskCount: 3 });
  });
  it('tasks_ready before evidence_ready and before partial still lands in the right area', () => {
    const state = run([tasks, evidence, partial], submitted());
    expect(state).toMatchObject({ phase: 'preliminary', evidenceReady: true, tasksReady: true });
  });
  it('final classifications replace provisional ones and a late partial never regresses the card', () => {
    const final = run([partial, evidence, tasks, saved], submitted());
    expect(final.phase).toBe('final');
    expect(final.finalClassifications?.feasibility).toBe('조건부 가능');
    expect(run([partial], final)).toMatchObject({ phase: 'final', finalClassifications: expect.any(Object) });
    expect(run([partial], final).preliminary?.classifications.feasibility).toBe('가능');
  });
  it('final without any earlier partial is fine (old backend)', () => {
    expect(run([saved], submitted())).toMatchObject({ phase: 'final', evidenceReady: true, tasksReady: true });
  });
  it('ignores events of another request and repeated events', () => {
    const other: ProgressAction = { type: 'event', event: { type: 'judgment.partial', request_id: 'zzz', payload: { classifications: { ai_need: '불필요' } } } };
    expect(run([other], submitted())).toEqual(submitted());
    expect(run([partial, partial], submitted())).toEqual(run([partial], submitted()));
  });
  it('tracks the current step from run.step and marks failure from judgment_failed', () => {
    const stepping = run([{ type: 'event', event: { type: 'run.step', request_id: 'r1', step_name: '근거 연결', payload: { status: 'running' } } }], submitted());
    expect(stepping.currentStep).toBe('근거 연결');
    expect(stepping.steps).toEqual([{ name: '근거 연결', status: 'running' }]);
    const done = run([{ type: 'event', event: { type: 'run.step', request_id: 'r1', step_name: '근거 연결', payload: { status: 'succeeded' } } }], stepping);
    expect(done.steps).toEqual([{ name: '근거 연결', status: 'succeeded' }]);
    expect(run([{ type: 'event', event: { type: 'judgment_failed', request_id: 'r1', payload: {} } }], done)).toMatchObject({ phase: 'failed' });
  });
});

describe('restore from the progress API (reload / reconnect)', () => {
  const snapshot = { request_id: 'r1', run_id: 'run1', status: 'processing', steps: [{ name: 'Jev 판단', kind: 'ai', status: 'succeeded' }, { name: '근거 연결', kind: 'ai', status: 'running' }], preliminary: { classifications: { ai_need: '필요' }, confidences: {}, risk_flags: {} }, evidence_ready: false, tasks_ready: false, final: false, timings_ms: { received_to_preliminary: 900, received_to_final: 0 } };
  it('rebuilds the steps and provisional card without any event', () => {
    const state = run([{ type: 'restore', progress: snapshot }]);
    expect(state).toMatchObject({ requestId: 'r1', phase: 'preliminary', currentStep: '근거 연결', evidenceReady: false });
    expect(state.preliminary?.classifications.ai_need).toBe('필요');
  });
  it('empty preliminary means still received; final=true means final; failed status means failed', () => {
    expect(run([{ type: 'restore', progress: { ...snapshot, preliminary: {}, steps: [] } }]).phase).toBe('received');
    expect(run([{ type: 'restore', progress: { ...snapshot, final: true, status: 'judgment_saved' } }]).phase).toBe('final');
    expect(run([{ type: 'restore', progress: { ...snapshot, status: 'failed' } }]).phase).toBe('failed');
  });
  it('never regresses state that events already advanced', () => {
    const state = run([partial, evidence], submitted());
    expect(run([{ type: 'restore', progress: { ...snapshot, preliminary: {}, steps: [] } }], state)).toMatchObject({ phase: 'preliminary', evidenceReady: true });
  });
});
