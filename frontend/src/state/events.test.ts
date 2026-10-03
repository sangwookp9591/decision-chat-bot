import { describe, expect, it } from 'vitest';
import { acceptEventSeq } from './events';

describe('SSE sequence ordering', () => {
  it('accepts only strictly increasing integer sequence IDs', () => {
    expect(acceptEventSeq(8, 7)).toBe(true);
    expect(acceptEventSeq(7, 7)).toBe(false);
    expect(acceptEventSeq(6, 7)).toBe(false);
    expect(acceptEventSeq(Number.NaN, 7)).toBe(false);
  });
});
