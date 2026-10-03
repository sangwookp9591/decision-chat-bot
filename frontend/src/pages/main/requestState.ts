import type { Judgment, RequestDetail } from '../../api/requests';
import type { StatusKind } from '../../components';
import { getStatusPresentation } from '../../components/statusLabels';

const INFO_STATUSES = ['보완 필요', 'needs_info', 'info_requested'];
const REJECTED_STATUSES = ['반려', 'rejected'];
const ASSIGNED_STATUSES = ['배정 완료', 'assigned'];
export const needsInfo = (status?: string) => INFO_STATUSES.includes(status || '');

/** What the reviewer asked the requester to supplement; the server stores needed_info as a JSON string. */
export function infoRequest(detail: RequestDetail | null): { reason: string; needed: string[] } | null {
  if (!detail || !needsInfo(detail.request.status)) return null;
  const raw = detail.request.needed_info;
  let list: unknown = raw;
  if (typeof raw === 'string') { try { list = JSON.parse(raw); } catch { list = [raw]; } }
  const needed = Array.isArray(list) ? list.map(String).filter(Boolean) : [];
  const reason = String(detail.request.info_requested || needed[0] || '');
  return { reason, needed: needed.filter((item) => item !== reason) };
}

/** Badge for the analysis card / result: the request's own status wins over the (possibly stale) pending review. */
export function resultBadge(detail: RequestDetail | null, judgment: Judgment | null, failed: boolean): { status: StatusKind; label: string } {
  const status = detail?.request.status || '';
  if (failed) return { status: 'failure', label: '시스템 실패' };
  if (needsInfo(status)) return { status: 'review', label: '보완 필요 · 정보 요청' };
  if (REJECTED_STATUSES.includes(status)) return { status: 'failure', label: '반려됨' };
  if (ASSIGNED_STATUSES.includes(status)) return { status: 'success', label: '배정 완료' };
  if (status === 'needs_file_decision') return { status: 'review', label: '보완 필요 · 파일 선택' };
  if (judgment) return judgment.review ? { status: 'review', label: '검토 대기' } : { status: 'success', label: '판단 저장 완료' };
  const known = getStatusPresentation(status);
  return known.known && status ? { status: known.status, label: known.label } : { status: 'progress', label: '분석 중' };
}
