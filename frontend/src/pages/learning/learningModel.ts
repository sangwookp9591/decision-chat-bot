import type { CandidateDetail, EffectVerdict, Predicate, RuleVersionRow, ValidationResult } from '../../api/learning';

export { fieldLabels, fieldLabel } from '../../lib/labels';
import { fieldLabel, ruleDecisionLabel } from '../../lib/labels';
export const sourceLabel = (source: string) => source === 'ai' ? 'AI 가설' : '사람 제안';

export type CandidateFilter = 'all' | 'review' | 'insufficient' | 'approved' | 'rejected';
export const filterLabels: Record<CandidateFilter, string> = { all: '전체', review: '검토 필요', insufficient: '자료 부족', approved: '승인', rejected: '기각' };
export function candidateFilterKey(status: string): Exclude<CandidateFilter, 'all'> {
  if (status === 'rejected') return 'rejected';
  if (status === 'approved') return 'approved';
  if (status === '자료 부족') return 'insufficient';
  return 'review';
}
export function candidateStatusLabel(status: string) {
  return { review: '검토 필요', insufficient: '자료 부족', approved: '승인 · 범위 확정', rejected: '기각' }[candidateFilterKey(status)];
}

export const versionStatusLabels: Record<string, string> = { validating: '검증 중', validated: '검증 완료', published: '게시 · 운영 중', stopped: '중단', reverted: '되돌림' };
export const versionStatusLabel = (status: string) => versionStatusLabels[status] || status;

export const effectLabels: Record<EffectVerdict, string> = { improved: '개선 확인', partial: '일부 확인', no_change: '변화 없음', worse: '악화', insufficient_sample: '관찰 중 · 표본 부족' };

/** 관찰 표본이 최소 기준에 못 미치면 효과를 판정하지 않는다는 문구. */
export function sampleShortage(sample: number, minimum: number): string | null {
  return sample < minimum ? `표본 부족: ${sample}건 / 최소 ${minimum}건 — 효과를 확정하지 않습니다.` : null;
}

export function validationNotice(result: Pick<ValidationResult, 'sample_count' | 'labeled_count'>, minimum: number): string[] {
  const notes = ['비교 검증 결과는 확정이 아닙니다. 게시 후 효과 관찰을 계속합니다.'];
  if (result.sample_count === 0) notes.push('비교할 표본이 없습니다.');
  else if (result.labeled_count === 0) notes.push('사람이 확정한 정답 표본이 없어 사람 수정 필요 변화를 비교할 수 없습니다.');
  else if (result.labeled_count < minimum) notes.push(`정답이 있는 표본이 ${result.labeled_count}건(최소 ${minimum}건 미만)이라 수정 감소를 확정할 수 없습니다.`);
  return notes;
}

export type Perms = { canView: boolean; canPropose: boolean; isAdmin: boolean };
export function permissions(roles: string[]): Perms {
  const has = (role: string) => roles.includes(role);
  return { canView: has('reviewer') || has('rule_admin') || has('operator'), canPropose: has('reviewer') || has('rule_admin'), isAdmin: has('rule_admin') };
}

export type ActionKey = 'approve' | 'approve_scope' | 'reject' | 'validate' | 'mark_validated' | 'publish' | 'stop' | 'revert';
export type ActionState = { enabled: boolean; reason: string | null };
const ADMIN_ONLY = '규칙 관리자만 실행할 수 있습니다.';
export type ActionContext = { candidate: CandidateDetail | null; version: RuleVersionRow | null; validationOk: boolean; revertTargets: number; retryDecision?: boolean };

/** 버튼 활성 여부와 비활성 이유. 서버가 최종 판단하며 화면은 이유를 미리 알려 줄 뿐이다. */
export function actionStates(perms: Perms, ctx: ActionContext): Record<ActionKey, ActionState> {
  const key = ctx.candidate ? candidateFilterKey(ctx.candidate.status) : null;
  const candidateOpen = !!ctx.candidate && !ctx.version && (ctx.retryDecision || (key !== 'approved' && key !== 'rejected'));
  const decide: ActionState = !perms.isAdmin ? { enabled: false, reason: ADMIN_ONLY } : candidateOpen ? { enabled: true, reason: null } : { enabled: false, reason: '이미 결정된 후보입니다.' };
  const onVersion = (statuses: string[], why: string): ActionState => !perms.isAdmin ? { enabled: false, reason: ADMIN_ONLY }
    : !ctx.version ? { enabled: false, reason: '승인된 규칙 버전이 없습니다.' }
    : statuses.includes(ctx.version.status) ? { enabled: true, reason: null } : { enabled: false, reason: why };
  const validate = onVersion(['validating'], '검증 중 상태의 버전만 검증할 수 있습니다.');
  const mark = onVersion(['validating'], '검증 중 상태의 버전만 검증 완료로 표시할 수 있습니다.');
  if (mark.enabled && !ctx.validationOk) { mark.enabled = false; mark.reason = '부작용 0건인 완료 검증 결과가 필요합니다.'; }
  const revert = onVersion(['published', 'stopped', 'reverted'], '게시한 적이 있는 규칙만 되돌릴 수 있습니다.');
  if (revert.enabled && ctx.revertTargets === 0) { revert.enabled = false; revert.reason = '되돌릴 대상 버전이 없습니다.'; }
  return {
    approve: decide, approve_scope: decide, reject: decide, validate, mark_validated: mark,
    publish: onVersion(['validated'], '검증을 완료하지 않은 규칙은 게시할 수 없습니다.'),
    stop: onVersion(['published'], '운영 중인 규칙만 중단할 수 있습니다.'), revert,
  };
}

/** 규칙 ID 기본값: R-<판단 항목>-NN. 이미 쓰는 번호는 건너뛴다. 서버 형식 ^R-[A-Z_]+-[0-9]{2,}$ */
export function suggestRuleId(field: string, existing: string[]): string {
  const base = `R-${field.toUpperCase().replace(/[^A-Z_]/g, '_')}`;
  let n = 1;
  while (existing.includes(`${base}-${String(n).padStart(2, '0')}`)) n += 1;
  return `${base}-${String(n).padStart(2, '0')}`;
}
export const RULE_ID_PATTERN = /^R-[A-Z_]+-[0-9]{2,}$/;

const opText: Record<string, string> = { eq: '=', in: '∈', gte: '≥', lte: '≤' };
export function describePredicate(p: Predicate): string {
  if (p.field) return `${fieldLabel(p.field)} ${opText[p.op || ''] || p.op} ${Array.isArray(p.value) ? p.value.join(', ') : String(p.value)}`;
  if (p.signal) return `신호 ${p.signal} ${opText[p.op || ''] || p.op} ${String(p.value)}`;
  if (p.catalog_task) return `카탈로그 업무 ${p.catalog_task} ${p.present === false ? '없음' : '있음'}`;
  if (p.requester_org) return `요청 조직 ${p.requester_org}`;
  return JSON.stringify(p);
}
export const describeScope = (predicates: Predicate[]) => predicates.length ? predicates.map(describePredicate).join(' · ') : '조건 없음 (모든 요청)';

const plain = (value: unknown): string => typeof value === 'string' ? value : Array.isArray(value) ? value.map(plain).join(', ') : JSON.stringify(value);
export function describeAction(action: Record<string, unknown>): string {
  if ('set' in action) return `값을 ${plain(action.set)}(으)로 설정`;
  if ('add' in action) return `협업 조직에 ${plain(action.add)} 추가`;
  if ('require_review' in action) return `검토 전환: ${plain(action.require_review)}`;
  return JSON.stringify(action);
}

export { percent } from '../../lib/format';
export const millis = (value: number | null | undefined) => value === null || value === undefined ? '미수집' : `${Math.round(value)}ms`;
export function isoOf(value: unknown): string {
  return typeof value === 'string' ? value : '';
}
import { formatTime as formatSharedTime } from '../../lib/format';
export const formatTime = (value: unknown) => formatSharedTime(value, { hour12: false });
export const valueText = (value: unknown) => value === null || value === undefined ? '—' : typeof value === 'string' ? value : JSON.stringify(value);

/** Both dates are required and the start must not be after the end; returns the Korean hint or ''. */
export function validationRangeProblem(range: { from: string; to: string }): string {
  const from = new Date(range.from), to = new Date(range.to);
  if (!range.from || !range.to || Number.isNaN(from.getTime()) || Number.isNaN(to.getTime())) return '시작과 끝 날짜를 모두 올바르게 입력해 주세요.';
  return from > to ? '시작은 끝보다 앞서야 합니다.' : '';
}

/** Timeline text of a rule decision node: "approve. 사유: … . 확정 범위 {json}" becomes plain Korean. */
export function ruleDecisionDetail(summary: string | null | undefined, fallback: string): string {
  const match = /^(\w+)\. 사유: (.*?)\. 확정 범위 (.*)$/s.exec(summary || '');
  if (!match) return summary || fallback;
  let scope = match[3];
  try { const parsed = JSON.parse(match[3]); scope = parsed && Array.isArray(parsed.all) ? describeScope(parsed.all) : parsed === null ? '지정 없음' : match[3]; } catch { /* keep raw text */ }
  return `${ruleDecisionLabel(match[1])} · 사유: ${match[2]} · 확정 범위: ${scope}`;
}
