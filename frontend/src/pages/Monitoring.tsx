import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button, LoadingState } from '../components';
import { monitoringApi, type MonitoringSummary, type Slo, type Alert } from '../api/monitoring';
import type { ApiError } from '../api/client';
import { formatTime, percent } from '../lib/format';
import './monitoring/monitoring.css';

const fmt = (value: number | null | undefined, unit = '') => value == null || !Number.isFinite(value) ? '미수집' : `${new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 2 }).format(value)}${unit}`;
const duration = (value: number | null | undefined) => value == null ? '미수집' : value < 1000 ? `${Math.round(value)}ms` : `${(value / 1000).toFixed(2)}초`;
const pct = (value: number | null | undefined) => percent(value, 2);
const dateInput = (date: Date) => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
const causes: Record<string, string> = { external_model: '외부 모델', parsing: '파싱', storage: '저장', sse: 'SSE', other: '기타' };
const steps: Record<string, string> = { intake_p95: '접수 응답', text_first_p95: '텍스트 최초 판단', attachment_first_p95: '첨부 최초 판단', sse_deliver_p95: 'SSE 전달', revision_p95: '재판단', step_p95: '단계 전체' };

const toIso = (value: string) => { const date = new Date(value); return value && !Number.isNaN(date.getTime()) ? date.toISOString() : null; };
/** Input problems of the period filter, shown next to the form instead of throwing from `toISOString`. */
export function rangeProblem(range: { from: string; to: string }): string {
  const from = toIso(range.from), to = toIso(range.to);
  if (!from || !to) return '시작과 종료 시각을 모두 올바르게 입력해 주세요.';
  return from > to ? '시작 시각은 종료 시각보다 앞서야 합니다.' : '';
}
const traceLink = (row: { request_id?: string; run_id?: string }) => { const query = new URLSearchParams(); if (row.request_id) query.set('request_id', row.request_id); if (row.run_id) query.set('run_id', row.run_id); return query.toString() ? `/observatory?${query}` : ''; };

export function Monitoring() {
  const [range, setRange] = useState(() => ({ from: dateInput(new Date(Date.now() - 30 * 86400000)), to: dateInput(new Date()) }));
  const [filters, setFilters] = useState({ org: '', status: '', version: '' });
  const [applied, setApplied] = useState({ range, filters });
  const problem = rangeProblem(range);
  const [data, setData] = useState<MonitoringSummary | null>(null); const [slo, setSlo] = useState<Slo | null>(null); const [alerts, setAlerts] = useState<Alert['alerts']>([]);
  const [error, setError] = useState(''); const [accessDenied, setAccessDenied] = useState(false); const [loading, setLoading] = useState(true); const [updated, setUpdated] = useState<string | null>(null);
  const load = useCallback(async () => { setLoading(true); setError(''); const query = { from: toIso(applied.range.from)!, to: toIso(applied.range.to)!, ...applied.filters };
    const result = await Promise.allSettled([monitoringApi.summary(query), monitoringApi.slo(), monitoringApi.failures(query), monitoringApi.alerts()]);
    const [summaryResult, sloResult, failuresResult, alertsResult] = result;
    const summary = summaryResult.status === 'fulfilled' ? summaryResult.value : null;
    const failures = failuresResult.status === 'fulfilled' ? failuresResult.value : null;
    if (summary) {
      setAccessDenied(false);
      setData(failures ? { ...summary, failures: failures.causes, unscoped_events: Math.max(summary.unscoped_events, failures.unscoped_events) } : summary);
      setUpdated(new Date().toISOString());
    } else {
      const failure = summaryResult.status === 'rejected' ? summaryResult.reason as ApiError : undefined;
      setAccessDenied(failure?.status === 403);
      setError(failure?.message || '집계를 불러오지 못했습니다.');
    }
    if (sloResult.status === 'fulfilled') setSlo(sloResult.value);
    if (alertsResult.status === 'fulfilled') setAlerts(alertsResult.value.alerts);
    setLoading(false);
  }, [applied]);
  useEffect(() => { void load(); }, [load]);
  if (loading && !data) return <LoadingState label="모니터링 집계 불러오는 중" />;
  if (error && !data && accessDenied) return <section className="monitor-page"><h1>모니터링</h1><div className="monitor-banner" role="status"><strong>운영자 권한 필요</strong><p>모니터링 집계는 운영자만 조회할 수 있습니다.</p></div></section>;
  const collection = data?.collection || slo?.collection; const incomplete = collection && !collection.complete;
  const kpis = [
    ['요청 수', data ? data.requests.received + data.requests.failed_before_id : null], ['자동 처리', data?.business?.auto_assignment_count ?? null], ['검토 대기', data?.review_wait_ms.unresolved ?? null], ['검토 완료', data?.business?.review_completed_count ?? null],
    ['실패', data ? data.availability.failed_calls + data.judgment.failed_runs : null], ['시간초과', data?.judgment.failed_120s ?? null], ['취소', data?.cancellations ?? null], ['섀도 실행', data?.shadow_runs ?? null],
  ] as const;
  const sloRows = [
    { name: '접수·조회 가용성', denominator: slo?.availability.total, target: '≥99.9%', targetValue: .999, current: slo?.availability.total ? (slo.availability.total - slo.availability.failures) / slo.availability.total : null, verified: slo?.availability.verified, metric: slo?.availability },
    { name: '최초 판단 저장 신뢰성', denominator: slo?.first_judgment.total, target: '≥99.0%', targetValue: .99, current: slo?.first_judgment.total ? (slo.first_judgment.total - slo.first_judgment.failures) / slo.first_judgment.total : null, verified: slo?.first_judgment.verified, metric: slo?.first_judgment },
  ];
  const failureRows = Object.entries(data?.failures || {}).flatMap(([cause, rows]) => rows.map((row) => ({ cause, ...row })));
  const statusName = (verified: boolean | undefined, current: number | null | undefined, target: number, incompleteCollection = false) => incompleteCollection ? '관측 불완전' : !verified ? '미검증' : current != null && current < target ? '미달' : '통과';
  return <section className="monitor-page"><header className="monitor-heading"><div><p className="eyebrow">JEV TRIAGE / OBSERVABILITY</p><h1>모니터링</h1><p>집계 기간 {data?.from ? formatTime(data.from, {}) : '—'} ~ {data?.to ? formatTime(data.to, {}) : '—'} · 갱신 {updated ? formatTime(updated, {}) : '미수집'}</p></div><Button variant="secondary" onClick={() => void load()}>새로고침</Button></header>
    <form className="monitor-filters" onSubmit={(e) => { e.preventDefault(); if (!problem) setApplied({ range, filters }); }}><label>시작 <input type="datetime-local" aria-invalid={!toIso(range.from)} value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} /></label><label>종료 <input type="datetime-local" aria-invalid={!toIso(range.to)} value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} /></label><label>조직 <input value={filters.org} onChange={(e) => setFilters({ ...filters, org: e.target.value })} placeholder="조직 ID" /></label><label>요청 상태 <input value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })} placeholder="예: review_pending" /></label><label>버전 <input value={filters.version} onChange={(e) => setFilters({ ...filters, version: e.target.value })} placeholder="Config/모델 버전" /></label><Button type="submit" disabled={Boolean(problem)}>적용</Button>{problem && <p className="monitor-field-error" role="alert">{problem}</p>}</form>
    {incomplete && <aside className="monitor-banner" role="alert"><strong>관측 불완전</strong><p>수집 누락 또는 수집기 중단이 감지됐습니다. 이 구간은 정상 0건으로 간주하지 않으며 SLO는 미검증입니다.</p><ul>{collection?.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul>{collection?.incomplete_intervals.map((interval, i) => <p key={`${interval.kind}-${i}`}>불완전 구간 {interval.kind} · {formatTime(interval.start_at, {})}</p>)}</aside>}
    {error && <div className="monitor-banner" role="alert">집계 필터 또는 API 오류: {error}</div>}
    <section className="monitor-panel"><h2>핵심 지표</h2><div className="monitor-kpis">{kpis.map(([label, value]) => <article key={label}><span>{label}</span><strong>{fmt(value)}</strong></article>)}</div><p className="monitor-note">자동 처리와 검토 완료는 요청 생성 기간의 영속 업무 집계입니다. 섀도 실행은 별도 집계입니다.</p></section>
    <section className="monitor-panel"><h2>서비스 수준 목표</h2><div className="monitor-table-scroll"><table><thead><tr><th>지표</th><th>분모</th><th>목표</th><th>현재</th><th>남은 예산</th><th>1시간 소진율</th><th>상태</th></tr></thead><tbody>{sloRows.map((row) => <tr key={row.name}><th>{row.name}</th><td>{fmt(row.denominator)}</td><td>{row.target}</td><td>{pct(row.current)}</td><td>{row.metric?.verified ? fmt(row.metric.remaining_failures, '건') : '미검증'}</td><td>{row.metric?.verified ? fmt(row.metric.burn_rate_1h, '×') : '미검증'}</td><td><span className={`monitor-state ${incomplete ? 'incomplete' : !row.verified ? 'unverified' : row.current != null && row.current < row.targetValue ? 'fail' : 'pass'}`}>{statusName(row.verified, row.current, row.targetValue, !!incomplete)}</span></td></tr>)}</tbody></table></div><p className="monitor-note">오류 예산은 완전한 연속 30일 관측일 때만 검증됩니다. {slo?.reason || ''}</p></section>
    <section className="monitor-columns"><section className="monitor-panel"><h2>시스템 지연 분포</h2><p>시스템 처리 시간이며 사람 검토 대기와 분리됩니다. 목표: 접수 p95 ≤2초, 텍스트 판단 ≤15초, 첨부 판단 ≤45초.</p><div className="monitor-table-scroll"><table><thead><tr><th>구간</th><th>p50</th><th>p95</th><th>표본</th></tr></thead><tbody>{Object.entries(steps).map(([key, label]) => { const v = data?.steps[key.replace('_p95','')]; const p95 = key === 'step_p95' ? data?.latency_ms.step_p95 : data?.latency_ms[key]; return <tr key={key}><th>{label}</th><td>{duration(v?.p50_ms)}</td><td>{duration(p95 ?? v?.p95_ms)}</td><td>{fmt(v?.count)}</td></tr>; })}</tbody></table></div></section>
      <section className="monitor-panel review-panel"><h2>사람 검토 대기</h2><p>시스템 SLO와 별도로 표시</p><div className="review-kpis">{[['p50', data?.review_wait_ms.p50], ['p95', data?.review_wait_ms.p95], ['최장', data?.review_wait_ms.longest], ['미처리', data?.review_wait_ms.unresolved]].map(([label, value]) => <article key={String(label)}><span>{label}</span><strong>{label === '미처리' ? fmt(value as number | null) : duration(value as number | null)}</strong></article>)}</div>{data?.review_wait_ms.source_status === 'unavailable' && <p role="status">업무 DB에서 검토 대기 정보를 가져오지 못했습니다.</p>}</section></section>
    <section className="monitor-columns"><section className="monitor-panel"><h2>실패 원인과 Trace</h2>{failureRows.length ? <ul className="failure-list">{failureRows.map((row, i) => <li key={`${row.attempt_id}-${i}`}><span>{causes[row.cause] || row.cause} · {row.error_class}</span><time>{formatTime(row.ts, {})}</time><div>{traceLink(row) ? <Link to={traceLink(row)}>Trace 보기{row.request_id ? ` · 요청 ${row.request_id}` : ''}{row.run_id ? ` · 실행 ${row.run_id}` : ''}</Link> : <span>연결된 요청·실행 없음</span>}{row.attempt_id && <span className="monitor-attempt"> 시도 {row.attempt_id}</span>}</div></li>)}</ul> : <p>해당 기간 실패 원인이 수집되지 않았습니다.</p>}</section>
      <section className="monitor-panel"><h2>알림</h2>{alerts.length ? <ul className="alert-list">{alerts.map((alert, i) => <li key={String(alert.id || alert.created_at || i)}><strong>{String(alert.title || alert.kind || alert.type || '운영 알림')}</strong><span>{String(alert.message || alert.summary || '')}</span><time>{String(alert.created_at || alert.ts || '')}</time></li>)}</ul> : <p>표시할 알림이 없습니다.</p>}</section></section>
    <footer className="monitor-foot">수집기 상태: {collection?.complete ? '정상' : collection ? '관측 불완전' : '미수집'} · 마지막 수집 {collection?.last_collected_at ? formatTime(collection.last_collected_at, {}) : '미수집'} · 미귀속 이벤트 {fmt(data?.unscoped_events)}</footer>
  </section>;
}
