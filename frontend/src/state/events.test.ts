import { afterEach, describe, expect, it, vi } from 'vitest';
import { acceptEventSeq, EVENT_KINDS, reconnectDelay, setEventCursorScope, lastEventSeq, streamUrl } from './events';

describe('SSE sequence ordering', () => {
  it('accepts only strictly increasing integer sequence IDs', () => {
    expect(acceptEventSeq(8, 7)).toBe(true);
    expect(acceptEventSeq(7, 7)).toBe(false);
    expect(acceptEventSeq(6, 7)).toBe(false);
    expect(acceptEventSeq(Number.NaN, 7)).toBe(false);
  });
});

const backendSources = import.meta.glob('../../../backend/jevtriage/**/*.py', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;

describe('event kinds', () => {
  it('subscribes to every kind the backend publishes', () => {
    const source = Object.values(backendSources).join('\n');
    const emitted = new Set<string>();
    for (const match of source.matchAll(/append_event(?:_in_tx)?\(\s*(?:tx,\s*)?[\w.]+,\s*['"]([a-z_.]+)['"]/g)) emitted.add(match[1]);
    for (const match of source.matchAll(/event_kind\s*=\s*['"]([a-z_.]+)['"]/g)) emitted.add(match[1]);
    for (const match of source.matchAll(/_mutate\(\s*tenant,\s*['"](rule\.[a-z_]+)['"]/g)) emitted.add(match[1]);

    for (const operation of ['publish', 'stop', 'revert']) emitted.add(`rule.${operation}`);
    expect(emitted.size).toBeGreaterThan(8);
    const subscribed = new Set<string>(EVENT_KINDS);
    expect([...emitted].filter((kind) => !subscribed.has(kind))).toEqual([]);
    // The client used to listen for kinds the server never sends.
    expect(['request.updated', 'run.updated', 'run.started', 'run.completed'].filter((kind) => subscribed.has(kind))).toEqual([]);
  });
});

describe('reconnect contract', () => {
  afterEach(() => sessionStorage.clear());
  it('connects with ?after= only and backs off exponentially up to 30s', () => {
    expect(streamUrl(12)).toBe('/api/events/stream?after=12');
    expect([0, 1, 2, 10].map(reconnectDelay)).toEqual([1000, 2000, 4000, 30000]);
  });
  it('scopes the stored cursor to tenant and user', () => {
    sessionStorage.setItem('jevtriage:last-event-seq:t-alpha:u1', '9');
    setEventCursorScope('t-alpha:u1'); expect(lastEventSeq()).toBe(9);
    setEventCursorScope('t-beta:u1'); expect(lastEventSeq()).toBe(0);
    vi.unstubAllGlobals();
  });
});
