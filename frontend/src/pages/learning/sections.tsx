import { Link } from 'react-router-dom';
import { RawDetails } from '../../components/RawDetails';
import type { CandidateDetail, CandidateExample, EffectMetrics, RuleEffects, RuleVersionRow, ValidationResult } from '../../api/learning';
import { describeAction, describeScope, effectLabels, fieldLabel, formatTime, millis, percent, sampleShortage, validationNotice, valueText, versionStatusLabel } from './learningModel';
import { comparisonConditionsLabel } from '../../lib/labels';

export const CYCLE = ['수정 기록', '가설', '검토된 규칙', '비교 검증', '게시', '효과 관찰'];

export function CycleStrip() {
  return <div className="learning-cycle">
    <ol aria-label="규칙 학습 순환">{CYCLE.map((step, i) => <li key={step}>{step}{i < CYCLE.length - 1 && <span aria-hidden="true"> →</span>}</li>)}</ol>
    <strong>모델 재학습 없음 · 규칙·컨텍스트로만 반영</strong>
  </div>;
}

export function ThreePanels({ corrections, candidates, rules }: { corrections: number | null; candidates: number; rules: number | null }) {
  return <div className="learning-panels">
    <div className="panel-fact"><b>관찰 사실</b><span>원문·입력·모델 반환·사람 수정. 수정 기록 {corrections ?? '—'}건</span></div>
    <div className="panel-hypothesis"><b>가설 (규칙 후보)</b><span>실행에 쓰이지 않음. 후보 {candidates}건</span></div>
    <div className="panel-rule"><b>승인된 규칙</b><span>권한자 승인 + 검증 후 게시. {rules === null ? '운영 중 수를 불러오지 못했습니다' : `운영 중 ${rules}건`}</span></div>
  </div>;
}

export function EvidenceTable({ examples, ruleRef }: { examples: CandidateExample[]; ruleRef: string | null }) {
  const first = examples[0]?.case.request_id;
  const mapLink = ruleRef ? `/judgment-map?rule_id=${encodeURIComponent(ruleRef)}` : first ? `/judgment-map?request_id=${encodeURIComponent(first)}` : null;
  return <section className="learning-card" aria-label="근거 수정 기록">
    <header><h3>근거가 된 수정 기록</h3>{mapLink && <Link to={mapLink}>판단 맵에서 경로 보기</Link>}</header>
    {examples.length === 0 ? <p className="learning-empty">연결된 수정 기록이 없습니다.</p> : <div className="table-scroll" tabIndex={0} aria-label="표, 좌우 화살표 키로 이동"><table>
      <caption className="sr-only">근거 수정 기록</caption>
      <thead><tr><th scope="col">요청</th><th scope="col">AI 원안 → 수정</th><th scope="col">수정자 · 시각</th><th scope="col">입력 · 실행 버전</th><th scope="col">관계</th></tr></thead>
      <tbody>{examples.map(({ role, case: c }) => {
        const isCorrection = 'field' in c && c.field !== undefined;
        return <tr key={`${role}-${c.id}`}>
          <td className="mono"><Link to={`/judgment-map?request_id=${encodeURIComponent(c.request_id)}`}>{c.request_id}</Link></td>
          <td>{isCorrection ? <>{fieldLabel(String(c.field))}: {valueText(c.ai_value)} → {valueText(c.corrected_value)}</> : 'AI 원안 유지 (수정 없음)'}</td>
          <td>{String(c.corrected_by || c.actor_id || '—')} · {formatTime(c.corrected_at || c.created_at)}</td>
          <td className="mono">{String(c.revision_id || '—')} · {String(c.run_id || '—')}{c.config_version !== undefined ? ` · v${c.config_version}` : ''}</td>
          <td><span className={`rel rel-${role}`}>{role === 'support' ? '지지' : '반례'}</span></td>
        </tr>;
      })}</tbody></table></div>}
  </section>;
}

function Delta({ label, base, candidate, note }: { label: string; base: number; candidate: number; note?: string }) {
  return <div className="learning-metric"><span>{label}</span><b>{base} → {candidate}</b><small>{note || (base === candidate ? '변화 없음' : candidate < base ? '감소' : '증가')}</small></div>;
}

/** `changes_by_value` keys are `<field>:<new value>`; show them as "담당 조직 · 주관 → 현업 8건". */
export function changeLabel(key: string, count: number) { const at = key.indexOf(':'); return at < 0 ? `${key} ${count}건` : `${fieldLabel(key.slice(0, at))} → ${key.slice(at + 1)} ${count}건`; }
export const failureCount = (result: Pick<ValidationResult, 'failures' | 'failure_count'>) => result.failure_count ?? (Array.isArray(result.failures) ? result.failures.length : Number(result.failures) || 0);

export function ValidationCard({ result, minimum }: { result: ValidationResult | null; minimum: number }) {
  if (!result) return <section className="learning-card" aria-label="비교 검증"><h3>비교 검증</h3><p className="learning-empty">이 규칙 버전의 비교 검증 결과가 이 화면에 없습니다. 검증을 실행하면 결과가 표시됩니다.</p></section>;
  const changes = Object.entries(result.changes_by_value || {});
  return <section className="learning-card" aria-label="비교 검증">
    <header><h3>비교 검증 · <span className="mono">{result.id}</span></h3><span className="learning-tag">섀도 실행 · 배정·알림 없음</span></header>
    <p>기준 Config v{result.base_config_version} ↔ 후보 {result.candidate_config_version} · {formatTime(result.from)} ~ {formatTime(result.to)}{result.scope_filter ? ` · 범위 ${result.scope_filter}` : ''} · 표본 {result.sample_count}건 · 사람 확정 정답 {result.labeled_count}건</p>
    <div className="learning-metrics">
      <div className="learning-metric"><span>분류 변경</span><b>{result.changed_count} / {result.sample_count}</b><small>{changes.length ? changes.map(([k, n]) => changeLabel(k, n)).join(' · ') : '변경 없음'}</small></div>
      <Delta label={`사람 수정 필요 (정답 ${result.labeled_count}건)`} base={result.human_correction_needed_base} candidate={result.human_correction_needed_candidate} />
      <Delta label="검토 전환" base={result.review_transition_base} candidate={result.review_transition_candidate} />
      <div className="learning-metric"><span>실패 · 호출</span><b>실패 {failureCount(result)} · 호출 {result.calls}/{result.max_calls}</b><small>지연은 재평가 검증에서 측정하지 않음 (미수집)</small></div>
    </div>
    <p className="learning-state">상태 {result.status === 'completed' ? '완료' : result.status === 'failed' ? '실패' : result.status} · 부작용 {result.side_effects}건</p>
    {validationNotice(result, minimum).map((note) => <p key={note} className="learning-caution">{note}</p>)}
  </section>;
}

export type TimelineItem = { kind: string; at?: string | null; actor?: string | null; detail: string; raw?: string; config_version?: number };
export function Timeline({ ruleLabel, items }: { ruleLabel: string; items: TimelineItem[] }) {
  return <section className="learning-card" aria-label="규칙 수명">
    <h3>{ruleLabel} 수명</h3>
    {items.length === 0 ? <p className="learning-empty">기록된 수명 단계가 없습니다.</p> : <ol className="learning-timeline">{items.map((item, i) => <li key={`${item.kind}-${i}`}>
      <b>{item.kind}</b><span>{item.detail}</span>{item.raw && item.raw !== item.detail && <RawDetails>{item.raw}</RawDetails>}<small>{formatTime(item.at)}{item.actor ? ` · ${item.actor}` : ''}{item.config_version !== undefined ? ` · Config v${item.config_version}` : ''}</small>
    </li>)}</ol>}
    <p className="learning-note">게시·중단·되돌리기는 새 Config 버전으로 기록되며 과거 실행은 그대로입니다. 진행 중 실행은 시작 시 고정한 버전으로 끝까지 처리됩니다.</p>
  </section>;
}

const metricRows = (m: EffectMetrics) => [String(m.labeled_count),percent(m.classification_change_rate), percent(m.correction_rate), percent(m.review_transition_rate), percent(m.failure_rate), `${millis(m.latency_p50_ms)} / ${millis(m.latency_p95_ms)} (n=${m.latency_sample_count})`];

export function Observation({ effects, state }: { effects: RuleEffects | null; state: 'none' | 'forbidden' | 'unpublished' | 'error' | 'ok' }) {
  if (state !== 'ok' || !effects) {
    const text = { none: '규칙 버전을 선택하면 게시 후 관찰이 표시됩니다.', forbidden: '게시 후 관찰 조회 권한이 없습니다.', unpublished: '아직 게시한 적이 없어 관찰 기록이 없습니다.', error: '효과 집계를 불러오지 못했습니다.', ok: '' }[state];
    return <section className="learning-card" aria-label="게시 후 관찰"><h3>게시 후 관찰</h3><p className="learning-empty">{text}</p></section>;
  }
  const { used, out_of_scope } = effects.groups;
  const shortage = effects.effect === 'insufficient_sample' ? sampleShortage(Math.min(effects.before_after.before.sample_count, effects.before_after.after.sample_count), effects.minimum_sample) : null;
  const m = [metricRows(effects.before_after.before), metricRows(effects.before_after.after), metricRows(used), metricRows(out_of_scope)];
  const labels = ['사람 확정 정답 표본 수', '분류 변경률', '사람 수정 발생률', '검토 전환율', '실패율', '지연 p50 / p95'];
  return <section className="learning-card" aria-label="게시 후 관찰">
    <header><h3>게시 후 관찰</h3><span className="learning-tag">{formatTime(effects.published_at)} 게시 · 전후 {effects.window_days}일</span></header>
    <div className="learning-metrics">
      <div className="learning-metric"><span>범위 안 실행 · 규칙 사용</span><b data-testid="used-count">{used.sample_count}</b></div>
      <div className="learning-metric"><span>범위 밖 · 미사용 기록</span><b data-testid="out-count">{out_of_scope.sample_count}</b></div>
      <div className="learning-metric"><span>사용 후 사람 수정</span><b>{used.corrections} / {used.sample_count}</b></div>
      <div className="learning-metric"><span>효과 판정</span><b data-testid="effect-verdict">{effectLabels[effects.effect]}</b></div>
    </div>
    {shortage && <p className="learning-caution">{shortage}</p>}
    <p className="learning-note">정답 정의: 사람이 승인 또는 수정 후 승인한 실행을 1건으로 셉니다. 미승인·기각·승인 대기와 수정 기록만 있는 실행은 정답으로 세지 않습니다.</p>
    {Math.min(effects.before_after.before.labeled_count, effects.before_after.after.labeled_count) < effects.minimum_sample && <p className="learning-caution">미확정: 사람 확정 정답 표본이 최소 {effects.minimum_sample}건에 미달합니다.</p>}
    <div className="table-scroll" tabIndex={0} aria-label="표, 좌우 화살표 키로 이동"><table>
      <caption className="sr-only">적용 전후와 사용·미사용 집단 비교</caption>
      <thead><tr><th scope="col">지표</th><th scope="col">게시 전 (n={effects.before_after.before.sample_count})</th><th scope="col">게시 후 (n={effects.before_after.after.sample_count})</th><th scope="col">사용 (n={used.sample_count})</th><th scope="col">범위 밖 (n={out_of_scope.sample_count})</th></tr></thead>
      <tbody>{labels.map((label, i) => <tr key={label}><th scope="row">{label}</th><td>{m[0][i]}</td><td>{m[1][i]}</td><td>{m[2][i]}</td><td>{m[3][i]}</td></tr>)}</tbody></table></div>
    <p className="learning-note">{comparisonConditionsLabel(effects.comparison_conditions)}. 관찰 관계이며 인과 효과를 보장하지 않습니다. 기존 SLO 분모와 별도 지표입니다(비교 검증 실행 {effects.shadow_runs_excluded}건 제외).</p>
  </section>;
}

export function RuleSummary({ candidate, version }: { candidate: CandidateDetail; version: RuleVersionRow | null }) {
  const body = version?.body || candidate.proposed_body;
  const confirmed = !!version;
  const u = candidate.uncertainty;
  const insufficient = candidate.status === '자료 부족';
  return <>
    <div className="learning-tags">
      <span className="mono">{candidate.id}{version ? ` → ${version.body.rule_id}@${version.version}` : ''}</span>
      <span className={`learning-tag ${candidate.source === 'ai' ? 'tag-ai' : 'tag-human'}`}>{candidate.source === 'ai' ? 'AI 가설' : '사람 제안'} · {candidate.author || '작성 주체 미기록'}{candidate.source === 'ai' ? ' · 집계 규칙(모델 생성 아님)' : ''}</span>
      {version && <span className="learning-tag tag-rule">{versionStatusLabel(version.status)}</span>}
      {(candidate.insufficient_approved || version?.insufficient_approved) && <span className="learning-tag tag-rule">{version?.insufficient_approval_label || candidate.insufficient_approval_label || '자료 부족 상태로 승인됨'}</span>}
      <span className="learning-tag">{body.effect === 'context' ? '컨텍스트 반영' : '규칙 반영'}</span>
    </div>
    <h2>{describeAction(body.action)} — {fieldLabel(candidate.field)}</h2>
    <p className="learning-hint">후보 문장은 결정적 규칙 본문에서 만든 것이며 실행에는 쓰이지 않습니다. {insufficient && <strong>자료 부족: 효과를 주장하지 않습니다.</strong>}</p>
    <div className="learning-facts">
      <div><span>적용 범위 ({confirmed ? '확정' : '제안'})</span><b>{describeScope(body.scope.all)}</b></div>
      <div><span>판단 항목</span><b>{fieldLabel(candidate.field)} · 대상 {fieldLabel(body.target)}</b></div>
      <div><span>불확실성</span><b>지지 {u.support_count ?? candidate.support_count ?? 0}건 · 반례 {u.counter_count ?? candidate.counter_count ?? 0}건{u.minimum_support ? ` · 최소 ${u.minimum_support}건` : ''}{u.single_organization_bias ? ' · 한 조직에 치우침' : ''}{u.rationale ? ` · ${u.rationale}` : ''}</b></div>
    </div>
    <p className="learning-invariant">필수 검토 조건(임상·안전·규제·긴급, 승인 전 배정 금지)은 이 규칙으로 바뀌지 않습니다. 저장할 때 서버가 자동으로 확인합니다.</p>
  </>;
}
