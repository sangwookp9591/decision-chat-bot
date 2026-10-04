import type { Judgment, RequestDetail } from '../../api/requests';
import { needsInfo } from './requestState';

/** What the single composer does for the open conversation. */
export type ComposerMode = 'new' | 'info' | 'file';
export const composerMode = (detail: RequestDetail | null): ComposerMode => (detail?.request.status === 'needs_file_decision' ? 'file' : needsInfo(detail?.request.status) ? 'info' : 'new');
export const revisionsApply = (mode: ComposerMode) => mode !== 'new';

export const EXAMPLE_REQUESTS = [
  'SAP 매출 CSV를 월별로 집계해 화면에 보여 주세요',
  '병원별 판매량으로 다음 달 수요를 예측하고 싶어요',
  '출하 지시가 멈췄어요. 오늘 마감이에요',
] as const;
export const ATTACH_LIMITS = 'PDF · DOCX · MD, 최대 5개 · 파일당 10 MiB · 합계 25 MiB';
export const MAX_FILES = 5;

export type UserMessage = { key: string; text: string; revision: number; requestId: string; files: Array<{ id: string; name: string; status: string }>; pending: boolean };
export type PendingSend = { text: string; files: string[]; baseRevision: number; requestId: string };
const revisionOf = (revision: RequestDetail['revisions'][number], index: number) => revision.number ?? revision.revision_number ?? index + 1;

const attachmentRevision = (file: unknown) => (file as { revision_id?: string }).revision_id;
const latestRevisionId = (detail: RequestDetail) => [...detail.revisions].sort((a, b) => (b.number ?? b.revision_number ?? 0) - (a.number ?? a.revision_number ?? 0))[0]?.id;
/** Attachments of the newest revision only: a revision carries the earlier files forward, so older copies would be listed twice. */
export function currentAttachments(detail: RequestDetail): RequestDetail['attachments'] {
  const latest = latestRevisionId(detail);
  return detail.attachments.some((file) => attachmentRevision(file)) ? detail.attachments.filter((file) => attachmentRevision(file) === latest) : detail.attachments;
}

/**
 * The user's side of the conversation, rebuilt from the saved revisions (so a reload restores it) plus an optimistic send.
 * The server stores each supplement revision as "previous text + new text" with the earlier files carried forward, so a bubble
 * shows only what that turn added.
 */
export function userMessages(detail: RequestDetail | null, pending: PendingSend | null): UserMessage[] {
  const ordered = (detail?.revisions || []).map((revision, index) => ({ revision, number: revisionOf(revision, index) })).sort((a, b) => a.number - b.number);
  const saved = ordered.map(({ revision, number }, index): UserMessage => {
    const before = index > 0 ? ordered[index - 1].revision : null;
    const prevText = before?.text || '';
    const text = revision.text || '';
    const earlier = new Set((detail?.attachments || []).filter((file) => before && attachmentRevision(file) === before.id).map((file) => file.filename));
    return {
      key: revision.id || `rev-${number}`, revision: number, pending: false, requestId: detail?.request.id || '',
      text: prevText && text.startsWith(prevText) ? text.slice(prevText.length).replace(/^\n/, '') : text,
      files: (detail?.attachments || []).filter((file) => attachmentRevision(file) === revision.id && !earlier.has(file.filename)).map((file) => ({ id: file.id, name: file.filename, status: file.status })),
    };
  });
  const currentRevision = detail ? detail.request.revision_number || detail.revisions.length : 0;
  // Optimistic until the saved revision shows up: same request and a newer revision than the one sent from.
  const confirmed = Boolean(pending?.requestId && detail?.request.id === pending.requestId && currentRevision > pending.baseRevision);
  if (pending && !confirmed) saved.push({ key: 'pending', revision: pending.baseRevision + 1, pending: true, requestId: pending.requestId, text: pending.text, files: pending.files.map((name, index) => ({ id: `pending-${index}`, name, status: 'pending' })) });
  return saved;
}

export type ResultMood = 'urgent' | 'review' | 'ok';
/** Icon rule from the design hand-off: urgent → warning with no mascot, review → surprised, otherwise like. */
export function resultMood(classifications: Record<string, unknown> | null | undefined, needsReview: boolean): ResultMood {
  const urgency = String(classifications?.urgency ?? '');
  if (urgency.includes('긴급') && !urgency.includes('불')) return 'urgent';
  return needsReview ? 'review' : 'ok';
}
export function judgmentMood(judgment: Judgment): ResultMood { return resultMood(judgment.classifications, Boolean(judgment.review) && !judgmentApproved(judgment)); }
const judgmentApproved = (judgment: Judgment) => ['approved', 'decided', '승인'].includes(String((judgment.review as { status?: string } | null)?.status || ''));

export const MOOD_TEXT: Record<ResultMood, string> = { urgent: '긴급 요청이에요. 사람의 확인이 필요해요', review: '확인이 조금 필요해요', ok: '요청을 정리했어요' };
