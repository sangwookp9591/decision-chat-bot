import { describe, expect, it } from 'vitest';
import type { RequestDetail } from '../../api/requests';
import { composerMode, currentAttachments, judgmentMood, resultMood, userMessages } from './conversation';
import type { Judgment } from '../../api/requests';

const detail = (status: string, revisions: Array<Record<string, unknown>>, attachments: Array<Record<string, unknown>> = []) => ({ request: { id: 'req_1', status, revision_number: revisions.length }, revisions, attachments }) as unknown as RequestDetail;

describe('composerMode', () => {
  it('turns the same input into a new request, a supplement answer or a re-attach', () => {
    expect(composerMode(null)).toBe('new');
    expect(composerMode(detail('judgment_saved', []))).toBe('new');
    expect(composerMode(detail('보완 필요', []))).toBe('info');
    expect(composerMode(detail('needs_file_decision', []))).toBe('file');
  });
});

describe('userMessages', () => {
  it('rebuilds right-hand bubbles per revision, in order, with the attachments of that revision', () => {
    const messages = userMessages(detail('judgment_saved', [{ id: 'r2', number: 2, text: '답변' }, { id: 'r1', number: 1, text: '요청' }], [{ id: 'a1', filename: 'a.pdf', status: 'ok', revision_id: 'r1' }]), null);
    expect(messages.map((m) => [m.revision, m.text, m.files.map((f) => f.name)])).toEqual([[1, '요청', ['a.pdf']], [2, '답변', []]]);
  });
  it('shows an optimistic bubble until the saved revision arrives, then drops it (no duplicate)', () => {
    const sending = { text: '새 요청', files: ['x.md'], baseRevision: 0, requestId: '' };
    expect(userMessages(null, sending)).toMatchObject([{ pending: true, text: '새 요청', files: [{ name: 'x.md' }] }]);
    expect(userMessages(null, { ...sending, requestId: 'req_1' })).toHaveLength(1); // accepted, detail not loaded yet
    expect(userMessages(detail('processing', [{ id: 'r1', number: 1, text: '새 요청' }]), { ...sending, requestId: 'req_1' }).map((m) => m.pending)).toEqual([false]);
  });
  it('keeps a supplement answer optimistic while the old revisions are on screen', () => {
    const old = detail('보완 필요', [{ id: 'r1', number: 1, text: '요청' }]);
    const answer = { text: '답', files: [], baseRevision: 1, requestId: 'req_1' };
    expect(userMessages(old, answer).map((m) => [m.revision, m.pending])).toEqual([[1, false], [2, true]]);
    expect(userMessages(detail('processing', [{ id: 'r1', number: 1, text: '요청' }, { id: 'r2', number: 2, text: '답' }]), answer).map((m) => m.pending)).toEqual([false, false]);
  });
});

describe('result icon rule', () => {
  it('urgent → warning without mascot, review needed → surprised, otherwise like', () => {
    expect(resultMood({ urgency: '긴급' }, false)).toBe('urgent');
    expect(resultMood({ urgency: '긴급' }, true)).toBe('urgent');
    expect(resultMood({ urgency: '일반' }, true)).toBe('review');
    expect(resultMood({ urgency: '일반' }, false)).toBe('ok');
    expect(resultMood({ urgency: '정보 부족' }, false)).toBe('ok');
    expect(judgmentMood({ classifications: { urgency: '일반' }, review: { status: 'pending' } } as unknown as Judgment)).toBe('review');
    expect(judgmentMood({ classifications: { urgency: '일반' }, review: { status: 'approved' } } as unknown as Judgment)).toBe('ok');
  });
});

describe('supplement revisions as stored by the server', () => {
  const rev1 = { id: 'r1', number: 1, text: '시설 점검 일정을 조회하고 싶어요' };
  const rev2 = { id: 'r2', number: 2, text: '시설 점검 일정을 조회하고 싶어요\n휴게실 3곳이에요' };
  const files = [{ id: 'a1', filename: 'broken.pdf', status: 'rejected', revision_id: 'r1' }, { id: 'a2', filename: 'broken.pdf', status: 'rejected', revision_id: 'r2' }, { id: 'a3', filename: 'fixed.md', status: 'ok', revision_id: 'r2' }];
  it('shows only the new text and the newly attached files in the follow-up bubble', () => {
    const [first, second] = userMessages(detail('needs_file_decision', [rev1, rev2], files), null);
    expect(first.files.map((f) => f.name)).toEqual(['broken.pdf']);
    expect(second.text).toBe('휴게실 3곳이에요'); expect(second.files.map((f) => f.name)).toEqual(['fixed.md']);
  });
  it('lists the unreadable file once: only the newest revision counts for the file choice', () => {
    expect(currentAttachments(detail('needs_file_decision', [rev1, rev2], files)).map((f) => f.id)).toEqual(['a2', 'a3']);
    expect(currentAttachments(detail('needs_file_decision', [rev1], [{ id: 'x', filename: 'a.pdf', status: 'rejected' }])).map((f) => f.id)).toEqual(['x']);
  });
});
