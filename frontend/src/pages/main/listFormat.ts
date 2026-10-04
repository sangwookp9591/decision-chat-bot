import type { RequestDetail } from '../../api/requests';

/** Display-only masking for the conversation list (the stored text is untouched). */
const MASKS: Array<[RegExp, string | ((match: string, ...groups: string[]) => string)]> = [
  [/(?<![\w.+-])([A-Z0-9])[A-Z0-9._%+-]*@([A-Z0-9-]+(?:\.[A-Z0-9-]+)+)/gi, (_m, first, domain) => `${first}***@${domain}`],
  [/(?<!\d)\d{6}[- ]?[1-8]\d{6}(?!\d)/g, '******-*******'],
  [/(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)/g, '**** **** **** ****'],
  [/(?<!\d)(?:\+82[- ]?0?|0)(?:1[016789]|2|[3-6][1-5])[- ]?\d{3,4}[- ]?\d{4}(?!\d)/g, '***-****-****'],
  [/(?<![A-Za-z0-9_-])(?:sk[_-](?:test[_-]|live[_-])?|AKIA|gh[pousr]_|AIza)[A-Za-z0-9_-]{20,}/g, '••••'],
  [/(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{32,}(?![A-Za-z0-9_-])/g, '••••'],
];
export function maskForDisplay(text: string): string {
  return MASKS.reduce((value, [pattern, replacement]) => value.replace(pattern, replacement as never), text);
}

const MAX_TITLE = 80;
/** First sentence of a request, one line, at most 80 characters (CSS adds the ellipsis when the row is narrower). */
export function firstSentence(text: string): string {
  const line = text.trim().split(/\r?\n/).find((part) => part.trim()) || '';
  const flat = line.replace(/\s+/g, ' ').trim();
  const sentence = /^(.+?[.!?。！？])(?:\s|$)/.exec(flat)?.[1] ?? flat;
  return sentence.length > MAX_TITLE ? `${sentence.slice(0, MAX_TITLE - 1)}…` : sentence;
}

/** Title for a list row: the first revision's first sentence (masked); attachment-only requests use the first file name. */
export function titleFromDetail(detail: Pick<RequestDetail, 'revisions' | 'attachments'> & Partial<RequestDetail>): string {
  const first = [...(detail.revisions || [])].sort((a, b) => (a.number ?? a.revision_number ?? 0) - (b.number ?? b.revision_number ?? 0))[0];
  const text = firstSentence(maskForDisplay(first?.text || ''));
  return text || (detail.attachments || [])[0]?.filename || '';
}

export const shortId = (id: string) => id.slice(0, 8);

/** Neo4j sends nanosecond fractions; Safari's Date parser only accepts milliseconds. */
function toDate(value: string | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value.replace(/(\.\d{3})\d+/, '$1'));
  return Number.isNaN(date.getTime()) ? null : date;
}
export function relativeTime(value: string | undefined, now: Date = new Date()): string {
  const date = toDate(value); if (!date) return '';
  const seconds = Math.max(0, Math.round((now.getTime() - date.getTime()) / 1000));
  if (seconds < 60) return '방금 전';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}분 전`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}시간 전`;
  if (seconds < 7 * 86400) return `${Math.floor(seconds / 86400)}일 전`;
  return `${date.getMonth() + 1}월 ${date.getDate()}일`;
}

/** ChatGPT-style date bucket for the conversation list: 오늘 / 어제 / 지난 7일 / 지난 30일 / "2026년 8월". Items without a date go last. */
export function groupLabel(value: string | undefined, now: Date = new Date()): string {
  const date = toDate(value); if (!date) return '이전';
  const day = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diff = Math.round((day(now) - day(date)) / 86_400_000);
  if (diff <= 0) return '오늘';
  if (diff === 1) return '어제';
  if (diff <= 7) return '지난 7일';
  if (diff <= 30) return '지난 30일';
  return `${date.getFullYear()}년 ${date.getMonth() + 1}월`;
}
