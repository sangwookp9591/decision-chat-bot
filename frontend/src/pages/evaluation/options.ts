/** Answer vocabulary for the evaluation labels. Values are stored exactly as in the backend OPTIONS (domain/questions.py). */
export type SingleField = { key: 'ai_need' | 'feasibility' | 'urgency'; kind: 'single'; options: string[]; uncertain: string };
export type MultiField = { key: 'team_set' | 'risk_areas'; kind: 'multi'; options: string[] };
export type LabelField = SingleField | MultiField;

export const LABEL_FIELDS: LabelField[] = [
  { key: 'ai_need', kind: 'single', options: ['필요', '불필요', '혼합'], uncertain: '정보 부족' },
  { key: 'feasibility', kind: 'single', options: ['가능', '조건부 가능', '현재 불가'], uncertain: '정보 부족' },
  { key: 'urgency', kind: 'single', options: ['긴급', '일반'], uncertain: '판단 보류' },
  { key: 'team_set', kind: 'multi', options: ['AI팀', 'IT팀', '현업'] },
  { key: 'risk_areas', kind: 'multi', options: ['임상·안전성 검토', '약물감시 검토', '규제 검토'] },
];
export const FIELD_KEYS = LABEL_FIELDS.map((field) => field.key);
/** Keys 1–4 jump to the first four fields. */
export const SHORTCUT_FIELDS = FIELD_KEYS.slice(0, 4);

export type Draft = Record<string, string | string[]>;

/** Draft from a stored decision or a proposal; single fields default to '' (unanswered), multi fields to []. */
export function draftFrom(source?: Record<string, unknown> | null): Draft {
  const draft: Draft = {};
  for (const field of LABEL_FIELDS) {
    const value = source?.[field.key];
    if (field.kind === 'multi') draft[field.key] = Array.isArray(value) ? value.map(String) : value ? [String(value)] : [];
    else draft[field.key] = typeof value === 'string' ? value : '';
  }
  return draft;
}
export const missingSingleFields = (draft: Draft) => LABEL_FIELDS.filter((field) => field.kind === 'single' && !draft[field.key]);
