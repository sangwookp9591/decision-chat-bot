import type { SourceDocument, SourceUnit } from '../api/requests';

export type SourceKind = SourceDocument['kind'];
export type ViewerTarget = { requestId: string; revision: string | number; source: string; unitId: string; title?: string };
export type UnitGroup = { key: string; heading: string | null; units: SourceUnit[] };

const num = (value: unknown) => (typeof value === 'number' ? value : Number(value));

/** Human label of a unit position: PDF page, DOCX paragraph, MD line, chat sentence. */
export function unitLabel(kind: SourceKind, location: Record<string, unknown>): string {
  if (kind === 'pdf' || location.page !== undefined) return `${num(location.page)}쪽`;
  if (kind === 'docx' || (location.paragraph !== undefined && kind !== 'chat')) return `문단 ${num(location.paragraph) + 1}`;
  if (kind === 'md' || location.line_start !== undefined) {
    const start = num(location.line_start), end = num(location.line_end ?? location.line_start);
    return end > start ? `${start}–${end}행` : `${start}행`;
  }
  return `문단 ${num(location.paragraph) + 1} · 문장 ${num(location.sentence) + 1}`;
}

/** PDF units are grouped by page so the viewer can draw page breaks; other kinds stay one flow. */
export function groupUnits(kind: SourceKind, units: SourceUnit[]): UnitGroup[] {
  if (kind !== 'pdf') return [{ key: 'all', heading: null, units }];
  const groups: UnitGroup[] = [];
  for (const unit of units) {
    const page = num(unit.location.page);
    const last = groups[groups.length - 1];
    if (last && last.key === `page-${page}`) last.units.push(unit);
    else groups.push({ key: `page-${page}`, heading: `${page}쪽`, units: [unit] });
  }
  return groups;
}

export const findAnchorIndex = (units: SourceUnit[], unitId: string) => units.findIndex((unit) => unit.unit_id === unitId);

/** scrollTop that centres the anchor unit in the scroll container, clamped to the scrollable range. */
export function anchorScrollTop(unitTop: number, unitHeight: number, containerHeight: number, scrollHeight: number): number {
  const centred = unitTop - (containerHeight - unitHeight) / 2;
  return Math.max(0, Math.min(Math.round(centred), Math.max(0, scrollHeight - containerHeight)));
}

export function noSourceNotice(canRead: boolean) {
  return canRead ? null : '원문 열람 권한 없음 — 근거 위치와 메타 정보만 표시합니다.';
}
