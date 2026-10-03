import { describe, expect, it } from 'vitest';
import { playbackPosition, type PlaybackEvent } from '../../api/observe';
const events: PlaybackEvent[] = [
 {type:'step_started',at:'2026-01-01T00:00:00Z',step_id:'a'},
 {type:'step_ended',at:'2026-01-01T00:00:01Z',step_id:'a',status:'succeeded'},
 {type:'step_started',at:'2026-01-01T00:00:02Z',step_id:'b'},
 {type:'step_ended',at:'2026-01-01T00:00:03Z',step_id:'b',status:'failed'},
 {type:'step_started',at:'2026-01-01T00:00:04Z',step_id:'c'},
 {type:'human_wait_started',at:'2026-01-01T00:00:05Z',review_id:'r'},
 {type:'human_wait_ended',at:'2026-01-01T02:00:05Z',review_id:'r',duration_ms:7200000},
];
describe('playbackPosition',()=>{
 it('stops at the failure and does not activate later steps',()=>{const p=playbackPosition(events,5000,['a','b','c']);expect(p.failed).toBe(true);expect(p.active.size).toBe(0);expect(p.reached).toBe(1)});
 it('retains skipped state without treating it as a successful step',()=>{const p=playbackPosition([{type:'step_started',at:'2026-01-01T00:00:00Z',step_id:'x'},{type:'step_ended',at:'2026-01-01T00:00:01Z',step_id:'x',status:'skipped'}],3000,['x']);expect(p.failed).toBe(false);expect(p.reached).toBe(0)});
 it('compresses human waiting while preserving its actual duration',()=>{const p=playbackPosition(events,0,['a','b','c']);expect(p.human).toEqual([{id:'r',compressed:true,actualMs:7200000}])});
 it('reveals the review-wait node (review:<id>) once its wait has started',()=>{const p=playbackPosition([{type:'step_started',at:'2026-01-01T00:00:00Z',step_id:'a'},{type:'step_ended',at:'2026-01-01T00:00:01Z',step_id:'a',status:'succeeded'},{type:'human_wait_started',at:'2026-01-01T00:00:02Z',review_id:'r1'}],Number.MAX_SAFE_INTEGER,['a','review:r1']);expect(p.reached).toBe(1);expect(p.failed).toBe(false)});
 it('keeps input order for events with the same timestamp',()=>{const p=playbackPosition([{type:'step_started',at:'2026-01-01T00:00:00Z',step_id:'x'},{type:'step_ended',at:'2026-01-01T00:00:00Z',step_id:'x',status:'failed'}],0,['x']);expect(p.active.size).toBe(0);expect(p.failed).toBe(true);expect(p.reached).toBe(0)});
 it('tracks reached steps by node id, independent of the display order of nodes',()=>{const p=playbackPosition(events.slice(0,2),5000,['c','b','a']);expect([...p.reachedIds]).toEqual(['a'])});
});
