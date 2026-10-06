import type { LlmConfig } from '../../api/llm';
import type { ReactNode } from 'react';
import type { PolicyConfig } from '../../api/policy';
import { ChipGroup, NumberField, Switch, TextField } from '../../components/fields';
import { policyFieldHint, policyFieldLabel, questionLabel } from '../../lib/labels';

/** Names for policy keys the shared label table does not cover (kept here so the form never shows an English key). */
const extra: Record<string, { label: string; hint: string }> = {
  noul_uncertain_band: { label: '확률 불확실 구간', hint: '확률이 이 구간 안에 있으면 “판단 불가”로 보고 사람 검토로 넘깁니다. 하한은 상한보다 작아야 합니다.' },
  learning: { label: '규칙 학습 기준', hint: '반복된 검토 결정에서 규칙 후보를 만들 때 쓰는 최소 기준입니다.' },
  masking: { label: '개인정보 마스킹', hint: '모델과 화면에 보내기 전에 가릴 개인정보 종류입니다.' },
  rules: { label: '학습된 규칙', hint: '규칙 학습 화면에서 승인된 규칙입니다.' },
  retention: { label: '보관 기간', hint: '기록별 보관 기간입니다. 운영 환경에서는 담당자가 기간을 확인해야 합니다.' },
};
export const policyLabel = (key: string) => extra[key]?.label || policyFieldLabel(key);
export const policyHint = (key: string) => extra[key]?.hint || policyFieldHint(key);

const itemLabels: Record<string, string> = {
  evidence: '근거 연결', catalog: '업무 목록 매칭',
  text_chars: '요청 본문 글자 수', attachments: '첨부 파일 수', file_bytes: '파일 1개 크기', total_bytes: '첨부 전체 크기', pdf_pages: 'PDF 쪽수',
  min_support: '규칙 후보 최소 근거 수', min_effect_sample: '효과 검증 최소 표본', shadow_max_calls: '비교 실행 최대 호출 수', effect_window_days: '효과 비교 기간',
  event_days: '이벤트 기록', idempotency_days: '중복 방지 기록', session_grace_days: '로그인 만료 유예', login_attempt_window_seconds: '로그인 시도 집계 창', journal_days: '처리 일지', metrics_days: '지표 기록', batch_size: '삭제 묶음 크기',
};
const itemLabel = (key: string) => itemLabels[key] || questionLabel(key);
const units: Record<string, string> = { text_chars: '자', attachments: '개', file_bytes: '바이트', total_bytes: '바이트', pdf_pages: '쪽', min_support: '건', min_effect_sample: '건', shadow_max_calls: '회', effect_window_days: '일', event_days: '일', idempotency_days: '일', session_grace_days: '일', journal_days: '일', metrics_days: '일', login_attempt_window_seconds: '초', batch_size: '건' };
const limitMax: Record<string, number> = { text_chars: 20000, attachments: 5, file_bytes: 10485760, total_bytes: 26214400, pdf_pages: 50 };
const ranges: Record<string, [number, number]> = { min_support: [2, 1000], min_effect_sample: [5, 100000], shadow_max_calls: [0, 200], effect_window_days: [1, 90], event_days: [1, 3650], idempotency_days: [1, 3650], session_grace_days: [0, 3650], login_attempt_window_seconds: [1, 2592000], journal_days: [1, 3650], metrics_days: [1, 3650], batch_size: [1, 10000] };
const maskLabels: Array<[string, string]> = [['registration', '주민·등록번호'], ['business', '사업자번호'], ['card', '카드번호'], ['email', '이메일'], ['phone', '전화번호'], ['account', '계좌번호'], ['ip', 'IP 주소'], ['url_query', 'URL 쿼리'], ['api_key', 'API 키']];

/** Keys the server sends beyond the shared PolicyConfig type. */
export type FullPolicyConfig = PolicyConfig & { llm?: LlmConfig; noul_uncertain_band?: number[]; learning?: Record<string, number>; masking?: { enabled: boolean; categories: string[] }; retention?: Record<string, number> };
type Props = {
  config: FullPolicyConfig; readOnly: boolean;
  set: (path: Array<string | number>, value: unknown) => void;
  invalid: (path: string, on: boolean) => void;
};

function Group({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  const body = (policyLabel(id) === title ? policyHint(id) : '');
  return <fieldset className="policy-group" data-policy-key={id} aria-label={title}>
    <legend>{title}</legend>
    {body && <p className="policy-hint">{body}</p>}
    <div className="policy-group-body">{children}</div>
    <details className="policy-tech"><summary>기술 상세</summary><code>{id}</code></details>
  </fieldset>;
}

const view = (conf: Record<string, unknown> | undefined) => conf ?? {};

/** Field-by-field policy editor. Locked keys (schema_version, auto_assign, rules) are shown but never editable. */
export function PolicyForm({ config, readOnly, set, invalid }: Props) {
  const num = (path: Array<string | number>, label: string, value: number, opts: { min?: number; max?: number; step?: number; unit?: string; hint?: string; error?: string } = {}) => {
    const key = path.join('.');
    return <NumberField key={key} label={label} hint={opts.hint} value={value} min={opts.min} max={opts.max} step={opts.step ?? 1} unit={opts.unit} disabled={readOnly} error={opts.error}
      onChange={(v) => { invalid(key, false); set(path, v); }} onInvalid={() => invalid(key, true)} />;
  };
  const prob = (path: Array<string | number>, label: string, value: number, hint?: string) => num(path, label, value, { min: 0, max: 1, step: 0.05, hint });
  const band = config.noul_uncertain_band ?? [0.35, 0.65];
  const bandError = band[0] >= band[1] ? '하한은 상한보다 작아야 합니다.' : '';
  const learning = view(config.learning) as Record<string, number>;
  const retention = view(config.retention) as Record<string, number>;
  const limits = config.limits ?? {};
  const masking = config.masking ?? { enabled: true, categories: [] };
  const flags = Object.entries(config.feature_flags ?? {});
  const groups = Object.entries(config.reviewer_groups ?? {});
  return <div className="policy-form">
    <Group id="choice_confidence_thresholds" title={policyLabel('choice_confidence_thresholds')}>
      {Object.entries(config.choice_confidence_thresholds ?? {}).map(([k, v]) => prob(['choice_confidence_thresholds', k], itemLabel(k), v))}
      {!Object.keys(config.choice_confidence_thresholds ?? {}).length && <p className="policy-none">지정된 항목이 없습니다.</p>}
    </Group>
    <Group id="noul_probability_thresholds" title={policyLabel('noul_probability_thresholds')}>
      {Object.entries(config.noul_probability_thresholds ?? {}).map(([k, v]) => prob(['noul_probability_thresholds', k], itemLabel(k), v))}
      {!Object.keys(config.noul_probability_thresholds ?? {}).length && <p className="policy-none">지정된 항목이 없습니다.</p>}
    </Group>
    <Group id="noul_uncertain_band" title={policyLabel('noul_uncertain_band')}>
      {num(['noul_uncertain_band', 0], '하한', band[0], { min: 0, max: 1, step: 0.05, error: bandError })}
      {num(['noul_uncertain_band', 1], '상한', band[1], { min: 0, max: 1, step: 0.05 })}
    </Group>
    <Group id="risk_clear_max" title={policyLabel('risk_clear_max')}>{prob(['risk_clear_max'], '확률 상한', config.risk_clear_max)}</Group>
    <Group id="evidence_noul_threshold" title={policyLabel('evidence_noul_threshold')}>{prob(['evidence_noul_threshold'], '확률 기준', config.evidence_noul_threshold)}</Group>
    <Group id="catalog_noul_threshold" title={policyLabel('catalog_noul_threshold')}>{prob(['catalog_noul_threshold'], '확률 기준', config.catalog_noul_threshold)}</Group>
    <Group id="reviewer_groups" title={policyLabel('reviewer_groups')}>
      {groups.map(([k, v]) => <TextField key={k} label={itemLabel(k)} hint="쉼표(,)로 구분해 그룹 이름을 적습니다." value={v.join(', ')} disabled={readOnly} onChange={(e) => set(['reviewer_groups', k], e.target.value.split(',').map((x) => x.trim()).filter(Boolean))} />)}
      {!groups.length && <p className="policy-none">지정된 검토자 그룹이 없습니다. 새 항목은 아래 ‘고급: JSON 보기’에서 추가합니다.</p>}
    </Group>
    <Group id="limits" title={policyLabel('limits')}>
      {Object.entries(limits).map(([k, v]) => num(['limits', k], itemLabel(k), v, { min: 0, max: limitMax[k], unit: units[k] }))}
    </Group>
    <Group id="feature_flags" title={policyLabel('feature_flags')}>
      {flags.map(([k, v]) => <Switch key={k} label={itemLabel(k)} checked={Boolean(v)} disabled={readOnly} onChange={(on) => set(['feature_flags', k], on)} />)}
      {!flags.length && <p className="policy-none">켜고 끌 기능이 아직 없습니다.</p>}
    </Group>
    <Group id="learning" title={policyLabel('learning')}>
      {Object.entries(learning).map(([k, v]) => num(['learning', k], itemLabel(k), v, { min: ranges[k]?.[0], max: ranges[k]?.[1], unit: units[k] }))}
    </Group>
    <Group id="masking" title={policyLabel('masking')}>
      <Switch label="마스킹 사용" checked={Boolean(masking.enabled)} disabled={readOnly} onChange={(on) => set(['masking', 'enabled'], on)} />
      <ChipGroup label="가릴 정보 종류" disabled={readOnly} options={maskLabels.map(([value, label]) => ({ value, label }))} value={masking.categories ?? []} onChange={(next) => set(['masking', 'categories'], maskLabels.map(([v]) => v).filter((v) => next.includes(v)))} />
    </Group>
    <Group id="retention" title={policyLabel('retention')}>
      {Object.entries(retention).map(([k, v]) => num(['retention', k], itemLabel(k), v, { min: ranges[k]?.[0], max: ranges[k]?.[1], unit: units[k] }))}
    </Group>
    <Group id="schema_version" title="잠금 항목">
      <p className="policy-locked"><strong>{policyLabel('schema_version')}</strong> {config.schema_version} · 직접 바꿀 수 없습니다.</p>
      <p className="policy-locked"><strong>{policyLabel('auto_assign')}</strong> {config.auto_assign ? '켜짐' : '꺼짐'} · 허용되지 않는 설정이라 잠겨 있습니다.</p>
      <p className="policy-locked"><strong>{policyLabel('rules')}</strong> {(config.rules ?? []).length}개 · 규칙 학습 화면에서 관리합니다.</p>
    </Group>
  </div>;
}
