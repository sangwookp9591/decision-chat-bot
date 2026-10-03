import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { learningApi, type CandidateDetail, type RuleDetail, type RuleEffects, type RuleScope, type RuleVersionRow, type ValidationResult } from '../api/learning';
import { policyApi } from '../api/policy';
import type { ApiError } from '../api/client';
import { ErrorState, LoadingState } from '../components';
import { Actions, type ActionHandlers } from './learning/Actions';
import { Observation, CycleStrip, EvidenceTable, RuleSummary, ThreePanels, Timeline, ValidationCard, type TimelineItem } from './learning/sections';
import { actionStates, candidateFilterKey, candidateStatusLabel, fieldLabel, filterLabels, isoOf, permissions, sourceLabel, suggestRuleId, versionStatusLabel, type CandidateFilter } from './learning/learningModel';
import './learning/learning.css';

type Pending = { candidateId: string; decisionId: string } | null;
const DEFAULT_MIN_SAMPLE = 20;
const message = (e: unknown) => {
  const err = e as ApiError;
  if (err.code === 'RULE_INVARIANT') return '규칙이 필수 검토나 안전 조건을 약화해 저장할 수 없습니다. 범위와 동작을 수정해 주세요.';
  if (err.code === 'INSUFFICIENT_ACK_REQUIRED') return '자료 부족 상태 확인과 10자 이상의 사유를 입력해 주세요.';
  return err.message || '요청을 처리하지 못했습니다.';
};

export function Learning({ roles }: { roles: string[] }) {
  const perms = useMemo(() => permissions(roles), [roles]);
  const [params, setParams] = useSearchParams();
  const [candidates, setCandidates] = useState<CandidateDetail[]>([]);
  const [corrections, setCorrections] = useState<number | null>(null);
  const [ruleDetails, setRuleDetails] = useState<RuleDetail[] | null>(null);
  const [filter, setFilter] = useState<CandidateFilter>('all');
  const [selectedId, setSelectedId] = useState<string | null>(params.get('candidate_id'));
  const [detail, setDetail] = useState<CandidateDetail | null>(null);
  const [versionNo, setVersionNo] = useState<number | null>(null);
  const [activeConfig, setActiveConfig] = useState(0);
  const [minSample, setMinSample] = useState(DEFAULT_MIN_SAMPLE);
  const [validations, setValidations] = useState<Record<string, ValidationResult>>({});
  const [effectResult, setEffectResult] = useState<{ state: 'none' | 'forbidden' | 'unpublished' | 'error' } | { state: 'ok'; effects: RuleEffects }>({ state: 'none' });
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [pending, setPending] = useState<Pending>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [list, active] = await Promise.all([learningApi.candidates(), policyApi.active()]);
      setCandidates(list); setActiveConfig(active.version);
      const configured = Number((active.config as unknown as { learning?: { min_effect_sample?: number } }).learning?.min_effect_sample);
      if (Number.isFinite(configured) && configured > 0) setMinSample(configured);
      setError('');
      learningApi.corrections().then((r) => setCorrections(r.corrections.length), () => setCorrections(null));
      if (perms.isAdmin) {
        const rules = await learningApi.rules();
        setRuleDetails(await Promise.all(rules.rules.map((r) => learningApi.rule(r.rule_id))));
      } else setRuleDetails(null);
    } catch (e) { setError(message(e)); } finally { setLoading(false); }
  }, [perms.isAdmin]);
  useEffect(() => { void load(); }, [load]);

  // The rule_id / config_version query parameters come from the judgment map links.
  useEffect(() => {
    const ruleRef = params.get('rule_id');
    if (!ruleRef || selectedId || !ruleDetails) return;
    const [rid, ver] = ruleRef.split('@');
    const hit = ruleDetails.find((r) => r.rule_id === rid)?.versions.filter((v) => !ver || v.version === Number(ver)).slice(-1)[0];
    if (hit?.body.candidate_id) setSelectedId(hit.body.candidate_id);
  }, [params, selectedId, ruleDetails]);

  const candidateVersions = useMemo(() => {
    const byCandidate = new Map<string, RuleVersionRow[]>();
    for (const rule of ruleDetails || []) for (const row of rule.versions) {
      const rows = byCandidate.get(row.body.candidate_id || '') || []; rows.push(row); byCandidate.set(row.body.candidate_id || '', rows);
    }
    for (const rows of byCandidate.values()) rows.sort((a, b) => a.version - b.version);
    return byCandidate;
  }, [ruleDetails]);
  const versionsFor = (candidateId: string) => candidateVersions.get(candidateId) || [];
  const version = useMemo(() => {
    if (!detail) return null;
    const all = versionsFor(detail.id);
    return all.find((v) => v.version === versionNo) || all.slice(-1)[0] || null;
  }, [detail, versionsFor, versionNo]);
  const ruleId = version?.body.rule_id || '';
  const currentRule = useMemo(() => ruleDetails?.find((rule) => rule.rule_id === ruleId) || null, [ruleDetails, ruleId]);
  const versions = detail ? versionsFor(detail.id) : [];
  const versionKey = version ? `${ruleId}@${version.version}` : '';

  useEffect(() => {
    if (!selectedId) { setDetail(null); return; }
    let live = true;
    learningApi.candidate(selectedId).then((d) => { if (live) setDetail(d); }, (e) => { if (live) setError(message(e)); });
    return () => { live = false; };
  }, [selectedId, candidates]);

  // Effects and lifecycle timeline follow the selected rule version (rule administrators only).
  useEffect(() => {
    setEffectResult({ state: 'none' }); setTimeline([]);
    if (!version || !detail) { setEffectResult({ state: 'none' }); return; }
    let live = true;
    learningApi.validations(ruleId, version.version).then(({ validations: rows }) => {
      if (live) setValidations((current) => ({ ...current, [versionKey]: rows[0] }));
    }, () => { if (live) setValidations((current) => { const next = { ...current }; delete next[versionKey]; return next; }); });
    learningApi.effects(ruleId).then((r) => { if (live) { setEffectResult({ state: 'ok', effects: r }); } }, (e: ApiError) => { if (live) setEffectResult({ state: e.status === 403 ? 'forbidden' : e.code === 'RULE_NOT_PUBLISHED' ? 'unpublished' : 'error' }); });
    (async () => {
      const items: TimelineItem[] = [{ kind: '후보 제안', at: isoOf(detail.created_at), actor: detail.author, detail: sourceLabel(detail.source) }];
      try {
        const { graphApi } = await import('../api/graph');
        const graph = await graphApi.judgment({ rule_id: versionKey });
        const decision = graph.nodes.find((n) => n.kind === 'RuleDecision');
        if (decision) items.push({ kind: decision.summary?.includes('scope') || decision.status === 'approve_with_scope_change' ? '범위 수정 후 승인' : '승인', at: decision.at, actor: decision.actor, detail: decision.summary || decision.title });
        const validation = graph.nodes.find((n) => n.kind === 'ValidationRun');
        if (validation) items.push({ kind: '비교 검증', at: validation.at, actor: validation.actor, detail: `${validation.id} · ${validation.status || ''}` });
        const config = new Set(currentRule?.versions.flatMap((v) => v.config_versions) || []);
        const first = Math.min(...(version.config_versions.length ? version.config_versions : [Infinity]));
        if (Number.isFinite(first)) {
          const history = (await policyApi.versions()).versions.filter((v) => v.version >= first).sort((a, b) => a.version - b.version).slice(0, 12);
          for (const row of history) {
            const d = await policyApi.version(row.version);
            const rules = (d.diff as Record<string, { before: Array<{ rule_id: string; version: number }>; after: Array<{ rule_id: string; version: number }> }>).rules;
            if (!rules) continue;
            const before = rules.before?.find((r) => r.rule_id === ruleId), after = rules.after?.find((r) => r.rule_id === ruleId);
            const everPublished = (currentRule?.versions.find((v) => v.version === after?.version)?.config_versions || []).sort((a, b) => a - b);
            if (after && after.version !== before?.version) items.push({ kind: everPublished[0] === row.version ? '게시 · 운영 중' : '되돌리기', at: row.created_at, actor: row.created_by, config_version: row.version, detail: `${ruleId}@${after.version} · ${row.reason}` });
            else if (before && !after && config.size) items.push({ kind: '중단', at: row.created_at, actor: row.created_by, config_version: row.version, detail: `${ruleId}@${before.version} · ${row.reason}` });
          }
        }
      } catch { /* timeline falls back to what could be read */ }
      if (live) setTimeline(items);
    })();
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [versionKey, detail?.id, ruleDetails]);

  const counts = useMemo(() => {
    const c: Record<CandidateFilter, number> = { all: candidates.length, review: 0, insufficient: 0, approved: 0, rejected: 0 };
    candidates.forEach((x) => { c[candidateFilterKey(x.status)] += 1; });
    return c;
  }, [candidates]);
  const shown = candidates.filter((c) => filter === 'all' || candidateFilterKey(c.status) === filter);
  const publishedRules = ruleDetails ? new Set(ruleDetails.filter((r) => r.versions.some((v) => v.status === 'published')).map((r) => r.rule_id)).size : null;
  const validation = versionKey ? validations[versionKey] || null : null;
  const revertTargets = version ? (currentRule?.versions || []).filter((v) => v.version !== version.version && ['published', 'stopped', 'reverted'].includes(v.status)).map((v) => v.version) : [];
  const retry = !!detail && pending?.candidateId === detail.id;
  const states = actionStates(perms, { candidate: detail, version, validationOk: !!validation && validation.status === 'completed' && validation.side_effects === 0, revertTargets: revertTargets.length, retryDecision: retry });
  const existingIds = (ruleDetails || []).map((r) => r.rule_id);

  async function run(label: string, work: () => Promise<void>) {
    setBusy(true); setNotice(''); setError('');
    try { await work(); setNotice(label); await load(); }
    catch (e) { const err = e as ApiError; setError(err.status === 403 ? `권한이 없습니다. ${err.message}` : message(e)); if (err.status === 409) await load(); }
    finally { setBusy(false); }
  }
  const expected = async () => (await policyApi.active()).version;
  const handlers: ActionHandlers = {
    approve: (rid, reason, scope?: RuleScope, acknowledgeInsufficient = false) => detail && void run(scope ? '범위를 수정해 승인하고 규칙 버전(검증 중)을 만들었습니다.' : '후보를 승인하고 규칙 버전(검증 중)을 만들었습니다.', async () => {
      let decisionId = retry ? pending!.decisionId : '';
      if (!decisionId) decisionId = (await learningApi.decide(detail.id, scope ? 'approve_with_scope_change' : 'approve', reason, scope, acknowledgeInsufficient)).decision_id;
      try { const created = await learningApi.createVersion(rid, decisionId, reason, acknowledgeInsufficient); setPending(null); setVersionNo(created.version); }
      catch (e) { setPending({ candidateId: detail.id, decisionId }); throw e; }
    }),
    reject: (reason) => detail && void run('후보를 기각했습니다. 기록은 보존됩니다.', async () => { await learningApi.decide(detail.id, 'reject', reason); }),
    validate: (range) => version && void run('비교 검증을 실행했습니다. 결과는 확정이 아닙니다.', async () => {
      const created = await learningApi.validate(ruleId, version.version, range);
      const result = await learningApi.validation(created.id);
      setValidations((current) => ({ ...current, [versionKey]: result }));
    }),
    markValidated: (reason) => version && validation && void run('검증 완료로 표시했습니다. 이제 게시할 수 있습니다.', async () => { await learningApi.markValidated(ruleId, version.version, validation.id, reason); }),
    publish: (reason) => version && void run(`새 Config 버전으로 게시했습니다. 게시 이후 시작한 실행부터 적용됩니다.`, async () => { await learningApi.publish(ruleId, version.version, await expected(), reason); }),
    stop: (reason) => version && void run('규칙을 중단했습니다. 진행 중 실행은 기존 버전으로 끝까지 처리됩니다.', async () => { await learningApi.stop(ruleId, await expected(), reason); }),
    revert: (to, reason) => version && void run(`v${to} 기준 새 Config 버전으로 되돌렸습니다.`, async () => { await learningApi.revert(ruleId, to, await expected(), reason); }),
  };
  async function generate() { await run('수정 기록에서 후보를 다시 집계했습니다.', async () => { await learningApi.generate(); }); }
  function choose(id: string) { setSelectedId(id); setVersionNo(null); setNotice(''); const next = new URLSearchParams(params); next.set('candidate_id', id); setParams(next, { replace: true }); }

  if (loading) return <LoadingState label="규칙 학습 불러오는 중" />;
  if (!perms.canView) return <section className="learning-page"><h1>규칙 학습</h1><ErrorState title="조회 권한이 없습니다">검토자·운영자·규칙 관리자만 볼 수 있습니다.</ErrorState></section>;
  const body = version?.body || detail?.proposed_body;
  return <section className="learning-page">
    <header className="learning-head"><div><p className="eyebrow">JEV TRIAGE</p><h1>규칙 학습</h1></div><button type="button" className="ui-button secondary" onClick={() => void load()}>새로고침</button></header>
    <CycleStrip />
    <ThreePanels corrections={corrections} candidates={candidates.length} rules={publishedRules} />
    {error && <p role="alert" className="learning-error">{error}</p>}
    {notice && <p role="status" className="learning-notice">{notice}</p>}
    <div className="learning-grid">
      <section aria-label="규칙 후보 목록" className="learning-list">
        <header><h2>규칙 후보</h2>
          <div className="learning-filters" role="group" aria-label="상태 필터">{(Object.keys(filterLabels) as CandidateFilter[]).map((key) => <button key={key} type="button" aria-pressed={filter === key} onClick={() => setFilter(key)}>{filterLabels[key]} {counts[key]}</button>)}</div>
          <button type="button" className="ui-button plain" disabled={busy || !perms.canPropose} title={perms.canPropose ? undefined : '검토자 이상만 후보를 집계할 수 있습니다.'} onClick={() => void generate()}>수정 기록에서 후보 집계</button>
        </header>
        {shown.length === 0 ? <p className="learning-empty">표시할 후보가 없습니다.</p> : <ul>{shown.map((c) => <li key={c.id}><button type="button" aria-current={c.id === selectedId} onClick={() => choose(c.id)}>
          <span className="mono">{c.id} · {fieldLabel(c.field)}</span><b>{candidateStatusLabel(c.status)}</b>
          <span>{sourceLabel(c.source)} · 지지 {c.support_count ?? 0} · 반례 {c.counter_count ?? 0}{c.status === '자료 부족' ? ` · ${c.uncertainty.minimum_support ?? ''}건 필요` : ''}</span>
        </button></li>)}</ul>}
      </section>
      <section aria-label="후보 상세" className="learning-detail">
        {!detail || !body ? <p className="learning-empty">왼쪽에서 후보를 선택하세요. 후보는 가설이며 실행에 쓰이지 않습니다.</p> : <>
          <div className="learning-card"><RuleSummary candidate={detail} version={version} />
            {ruleDetails && versions.length > 1 && <label className="learning-inline">규칙 버전<select value={version?.version} onChange={(e) => setVersionNo(Number(e.target.value))}>{versions.map((v) => <option key={v.version} value={v.version}>v{v.version} · {versionStatusLabel(v.status)}</option>)}</select></label>}
            {(detail.insufficient_approved || version?.insufficient_approved) && <p className="learning-caution" role="status">{version?.insufficient_approval_label || detail.insufficient_approval_label || '자료 부족 상태로 승인됨'}</p>}
            {perms.isAdmin && version && <p className="learning-state">버전 {versionKey} · 상태 {versionStatusLabel(version.status)} · 게시 Config {version.config_versions.length ? version.config_versions.map((v) => `v${v}`).join(', ') : '없음'} · 적용 기록 {version.application_count}건 · 활성 Config v{activeConfig}</p>}
            {!perms.isAdmin && <p className="learning-hint">규칙 버전·검증·효과는 규칙 관리자만 조회합니다.</p>}
          </div>
          <EvidenceTable examples={detail.examples} ruleRef={version ? versionKey : null} />
          {perms.isAdmin && <><ValidationCard result={validation} minimum={minSample} />
            <Timeline ruleLabel={version ? versionKey : detail.id} items={timeline.length ? timeline : [{ kind: '후보 제안', at: isoOf(detail.created_at), actor: detail.author, detail: sourceLabel(detail.source) }]} />
            <Observation effects={effectResult.state === 'ok' ? effectResult.effects : null} state={effectResult.state} /></>}
          <Actions key={`${detail.id}:${versionKey}:${retry}`} states={states} isAdmin={perms.isAdmin} busy={busy} handlers={handlers}
            defaultRuleId={retry || !version ? suggestRuleId(detail.field, existingIds) : ruleId} defaultScope={detail.proposed_body.scope as RuleScope}
            requiresInsufficientAck={detail.status === '자료 부족' || !!detail.insufficient_approved}
            revertTargets={revertTargets} showDecision={!version && candidateFilterKey(detail.status) !== 'rejected'} showVersion={!!version || !perms.isAdmin} retryDecision={retry ? pending!.decisionId : null} />
        </>}
      </section>
    </div>
  </section>;
}
