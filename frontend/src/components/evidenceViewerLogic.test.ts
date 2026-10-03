import { describe, expect, it } from 'vitest';
import type { SourceUnit } from '../api/requests';
import { anchorScrollTop, findAnchorIndex, groupUnits, noSourceNotice, unitLabel } from './evidenceViewerLogic';

const unit = (unit_id: string, location: Record<string, unknown>): SourceUnit => ({ unit_id, order: 0, location, char_start: 0, char_end: 1 });

describe('evidence viewer anchors', () => {
  it('labels PDF page, DOCX paragraph, MD line and chat sentence positions', () => {
    expect(unitLabel('pdf', { page: 3 })).toBe('3쪽');
    expect(unitLabel('docx', { paragraph: 4 })).toBe('문단 5');
    expect(unitLabel('md', { line_start: 7, line_end: 7 })).toBe('7행');
    expect(unitLabel('md', { line_start: 7, line_end: 9 })).toBe('7–9행');
    expect(unitLabel('chat', { paragraph: 1, sentence: 0 })).toBe('문단 2 · 문장 1');
  });
  it('groups PDF units per page and keeps other kinds in one flow', () => {
    const units = [unit('a', { page: 1 }), unit('b', { page: 1 }), unit('c', { page: 2 })];
    expect(groupUnits('pdf', units).map((g) => [g.heading, g.units.length])).toEqual([['1쪽', 2], ['2쪽', 1]]);
    expect(groupUnits('docx', units)).toHaveLength(1);
  });
  it('finds the anchor unit by unit_id and reports a miss as -1', () => {
    const units = [unit('a', {}), unit('b', {})];
    expect(findAnchorIndex(units, 'b')).toBe(1);
    expect(findAnchorIndex(units, 'zzz')).toBe(-1);
  });
  it('centres the anchor in the scroll container and clamps at both ends', () => {
    expect(anchorScrollTop(1000, 40, 400, 3000)).toBe(820);
    expect(anchorScrollTop(10, 40, 400, 3000)).toBe(0);
    expect(anchorScrollTop(2950, 40, 400, 3000)).toBe(2600);
    expect(anchorScrollTop(100, 40, 400, 300)).toBe(0);
  });
  it('explains missing source permission only when it is missing', () => {
    expect(noSourceNotice(false)).toContain('원문 열람 권한 없음');
    expect(noSourceNotice(true)).toBeNull();
  });
});
