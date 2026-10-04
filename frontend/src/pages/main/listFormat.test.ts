import { describe, expect, it } from 'vitest';
import { firstSentence, groupLabel, maskForDisplay, relativeTime, shortId, titleFromDetail } from './listFormat';

const NOW = new Date('2026-10-04T12:00:00Z');
describe('request list display helpers', () => {
  it('short id keeps the first 8 characters', () => {
    expect(shortId('req_0123456789abcdef')).toBe('req_0123');
    expect(shortId('req_1')).toBe('req_1');
  });
  it('relative time reads like a chat app', () => {
    expect(relativeTime('2026-10-04T11:59:40Z', NOW)).toBe('방금 전');
    expect(relativeTime('2026-10-04T11:57:00Z', NOW)).toBe('3분 전');
    expect(relativeTime('2026-10-04T09:00:00Z', NOW)).toBe('3시간 전');
    expect(relativeTime('2026-10-02T12:00:00Z', NOW)).toBe('2일 전');
    expect(relativeTime('2026-08-01T12:00:00Z', NOW)).toMatch(/^8월 1일/);
    expect(relativeTime(undefined, NOW)).toBe('');
    expect(relativeTime('not a date', NOW)).toBe('');
  });
  it('parses nanosecond timestamps (Neo4j) the way Safari needs', () => {
    expect(relativeTime('2026-10-04T11:57:00.123456789Z', NOW)).toBe('3분 전');
  });
  it('masks personal values before they reach the list', () => {
    expect(maskForDisplay('문의 hong.gildong@corp.com 로 회신')).not.toContain('hong.gildong');
    expect(maskForDisplay('연락처 010-1234-5678')).not.toContain('5678');
    expect(maskForDisplay('주민번호 900101-1234567')).not.toContain('1234567');
    expect(maskForDisplay('카드 1234 5678 9012 3456')).not.toContain('9012');
    expect(maskForDisplay(`토큰 ${['sk', 'live', 'abcdefghijklmnopqrstuvwxyz0123'].join('_')}`)).not.toContain('abcdefghij');
    expect(maskForDisplay('일반 문장입니다')).toBe('일반 문장입니다');
  });
  it('takes the first sentence, collapsed to one line', () => {
    expect(firstSentence('회의실 예약 화면이 필요합니다. 부서별로 보고 싶어요.')).toBe('회의실 예약 화면이 필요합니다.');
    expect(firstSentence('첫 줄\n둘째 줄')).toBe('첫 줄');
    expect(firstSentence('  공백   정리  ')).toBe('공백 정리');
    expect(firstSentence('a'.repeat(300)).length).toBeLessThanOrEqual(80);
    expect(firstSentence('')).toBe('');
  });
  it('title comes from the first revision, masked; attachment-only requests name the file', () => {
    const revisions = [{ id: 'r2', number: 2, text: '첫 요청 보완 답변' }, { id: 'r1', number: 1, text: '문의 a@b.co 요청입니다. 두번째' }];
    expect(titleFromDetail({ request: { id: 'x', status: 's' }, revisions, attachments: [] })).toBe('문의 a***@b.co 요청입니다.');
    expect(titleFromDetail({ request: { id: 'x', status: 's' }, revisions: [{ id: 'r', number: 1, text: '' }], attachments: [{ filename: 'spec.pdf' }] } as never)).toBe('spec.pdf');
    expect(titleFromDetail({ request: { id: 'x', status: 's' }, revisions: [], attachments: [] })).toBe('');
  });
  it('groups the conversation list by day like a chat sidebar', () => {
    const local = new Date(2026, 9, 4, 15, 0, 0); // 2026-10-04 local
    const at = (daysAgo: number, hour = 9) => new Date(2026, 9, 4 - daysAgo, hour, 0, 0).toISOString();
    expect(groupLabel(at(0, 1), local)).toBe('오늘');
    expect(groupLabel(at(1, 23), local)).toBe('어제');
    expect(groupLabel(at(5), local)).toBe('지난 7일');
    expect(groupLabel(at(20), local)).toBe('지난 30일');
    expect(groupLabel(new Date(2026, 7, 10).toISOString(), local)).toBe('2026년 8월');
    expect(groupLabel(undefined, local)).toBe('이전');
  });
});
