import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { EmptyState, ErrorState, LoadingState } from '../components';
import type { ApiError } from '../api/client';
import { graphApi, type GraphCriteria, type GraphEdge, type GraphNode, type JudgmentGraph, type NodeDetail } from '../api/graph';
import { MapView } from './judgment-map/MapView';
import { ListView } from './judgment-map/ListView';
import { Detail } from './judgment-map/Detail';
import { buildDisplay, computeHighlight, mergeGraph, neighborId, ruleVersionTabs, tabRuleId, versionScope, type DisplayItem } from './judgment-map/logic';
import './judgment-map/judgment-map.css';
import { statusText } from '../components/statusLabels';

const CRITERIA_FIELDS: Array<[keyof GraphCriteria, string]> = [['request_id', '요청 ID'], ['run_id', '실행 ID'], ['rule_id', '규칙 ID'], ['config_version', 'Config 버전'], ['status', '상태']];
const STATUSES = ['published', 'validated', 'validating', 'stopped', 'reverted', '제안', '자료 부족', 'approved', 'rejected', 'completed', 'active'];
const narrow = () => typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 760px)').matches;

export function JudgmentMap() {
  const [params, setParams] = useSearchParams();
  const criteria: GraphCriteria = useMemo(() => ({
    request_id: params.get('request_id') || undefined, run_id: params.get('run_id') || undefined, rule_id: params.get('rule_id') || undefined,
    config_version: params.get('config_version') || undefined, status: params.get('status') || undefined,
  }), [params]);
  const [draft, setDraft] = useState<GraphCriteria>(criteria);
  const [graph, setGraph] = useState<JudgmentGraph | null>(null);
  const [extra, setExtra] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] }>({ nodes: [], edges: [] });
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'map' | 'list'>(narrow() ? 'list' : 'map');
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<NodeDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [tabStop, setTabStop] = useState<string | null>(null);
  const [versionTab, setVersionTab] = useState<string | null>(null);
  const [big, setBig] = useState(false);
  const body = useRef<HTMLDivElement>(null);
  const bigToggle = useRef<HTMLButtonElement>(null);

  useEffect(() => setDraft(criteria), [criteria]);
  const loadSeq = useRef(0);
  const load = useCallback(async () => {
    const seq = ++loadSeq.current; // a slower response for older criteria must not overwrite the current graph
    setLoading(true); setError(null); setSelected(null); setDetail(null); setVersionTab(null); setExtra({ nodes: [], edges: [] }); setExpanded(new Set());
    try { const next = await graphApi.judgment(criteria); if (seq === loadSeq.current) setGraph(next); }
    catch (e) { if (seq === loadSeq.current) { setError(e as ApiError); setGraph(null); } }
    finally { if (seq === loadSeq.current) setLoading(false); }
  }, [criteria]);
  useEffect(() => { void load(); }, [load]);

  const allNodes = useMemo(() => mergeGraph(graph?.nodes || [], extra.nodes), [graph, extra]);
  const allEdges = useMemo(() => mergeGraph(graph?.edges || [], extra.edges), [graph, extra]);
  const versionTabs = useMemo(() => ruleVersionTabs(allNodes, tabRuleId(allNodes, criteria.rule_id)), [allNodes, criteria.rule_id]);
  const activeTab = versionTabs.find((tab) => tab.id === versionTab) || null;
  const scope = useMemo(() => (activeTab ? versionScope(allEdges, activeTab.id) : null), [activeTab, allEdges]);
  const nodes = useMemo(() => (scope ? allNodes.filter((n) => scope.nodeIds.has(n.id)) : allNodes), [allNodes, scope]);
  const edges = useMemo(() => (scope ? allEdges.filter((e) => scope.edgeIds.has(e.id)) : allEdges), [allEdges, scope]);
  const layers = useMemo(() => (graph?.layers || []).map((layer) => ({ ...layer, count: nodes.filter((n) => n.layer === layer.layer).length })), [graph, nodes]);
  const highlight = useMemo(() => computeHighlight(edges, selected), [edges, selected]);
  const displayItems: DisplayItem[] = useMemo(() => buildDisplay(nodes, expanded, highlight.nodeIds), [nodes, expanded, highlight]);
  const selectedNode = nodes.find((n) => n.id === selected) || null;
  const layerName = (layer: number) => layers.find((l) => l.layer === layer)?.name || String(layer);

  const select = useCallback(async (id: string | null) => {
    setSelected(id); setDetail(null);
    if (!id) return;
    setTabStop(id); setDetailLoading(true);
    const kind = nodes.find((n) => n.id === id)?.kind;
    try {
      const [info, path] = await Promise.all([graphApi.node(id, kind), graphApi.path(id, kind, 'both')]);
      setDetail(info);
      setExtra((current) => ({ nodes: mergeGraph(current.nodes, path.nodes), edges: mergeGraph(current.edges, path.edges) }));
    } catch (e) { setError(e as ApiError); }
    finally { setDetailLoading(false); }
  }, [nodes]);

  const pick = (item: DisplayItem) => {
    if (item.group) { setExpanded((current) => new Set(current).add(item.id)); return; }
    void select(item.id);
  };
  const pickVersion = (id: string | null) => { setVersionTab(id); setSelected(null); setDetail(null); };
  const leaveBig = () => { setBig(false); bigToggle.current?.focus(); };
  useEffect(() => {
    if (!big) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previous; };
  }, [big]);
  // Esc leaves the expanded view from anywhere in the page except an open dialog (it closes itself first).
  const onPageKeyDown = (event: React.KeyboardEvent) => {
    if (event.key !== 'Escape' || !big || (event.target as HTMLElement).closest('[role="dialog"]')) return;
    event.preventDefault(); leaveBig();
  };
  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Escape') {
      if (big) return; // the page handler leaves the expanded view first
      if (selected) { event.preventDefault(); void select(null); }
      return;
    }
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
    const target = (event.target as HTMLElement).closest<HTMLElement>('[data-node-id]');
    if (!target) return;
    const items: DisplayItem[] = view === 'map' ? displayItems : nodes.map((n) => ({ id: n.id, layer: n.layer, kind: n.kind, label: n.title, nodes: [n], group: false }));
    const next = neighborId(items, target.dataset.nodeId as string, event.key);
    if (!next) return;
    event.preventDefault();
    setTabStop(next);
    requestAnimationFrame(() => Array.from(body.current?.querySelectorAll<HTMLElement>('[data-node-id]') || []).find((el) => el.dataset.nodeId === next)?.focus());
  };
  const apply = (event: React.FormEvent) => {
    event.preventDefault();
    const next = new URLSearchParams();
    CRITERIA_FIELDS.forEach(([key]) => { const value = draft[key]?.trim(); if (value) next.set(key, value); });
    setParams(next);
  };
  const clear = (key: keyof GraphCriteria) => { const next = new URLSearchParams(params); next.delete(key); setParams(next); };
  const active = CRITERIA_FIELDS.filter(([key]) => criteria[key]);
  const firstStop = tabStop ?? displayItems[0]?.id ?? null;

  return <section className={`jm-page ${big ? 'is-expanded' : ''}`} onKeyDown={onPageKeyDown}>
    <header className="jm-heading">
      <div><p className="eyebrow">근거 → 가설 → 판단 → 적용 → 업무 단계</p><h1>입체 판단 맵</h1></div>
      <div role="group" aria-label="보기 방식" className="jm-toggle">
        <button type="button" aria-pressed={view === 'map'} onClick={() => setView('map')}>입체 맵</button>
        <button type="button" aria-pressed={view === 'list'} onClick={() => setView('list')}>목록 보기</button>
      </div>
      <button type="button" ref={bigToggle} className="jm-big" aria-pressed={big} onClick={() => setBig((value) => !value)}>크게 보기</button>
    </header>
    <form className="jm-filters" onSubmit={apply} aria-label="탐색 기준">
      <strong>탐색 기준</strong>
      {CRITERIA_FIELDS.map(([key, label]) => key === 'status'
        ? <label key={key}>{label}<select value={draft.status || ''} onChange={(e) => setDraft({ ...draft, status: e.target.value })}><option value="">전체</option>{STATUSES.map((s) => <option key={s} value={s}>{statusText(s)}</option>)}</select></label>
        : <label key={key}>{label}<input value={draft[key] || ''} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })} /></label>)}
      <button type="submit">적용</button>
      <button type="button" onClick={() => setParams(new URLSearchParams())}>초기화</button>
      <span className="jm-note">노드와 연결은 저장된 관계에서만 그립니다. 없는 관계는 만들지 않습니다.</span>
    </form>
    {active.length > 0 && <div className="jm-active" aria-label="적용된 기준">{active.map(([key, label]) => <button key={key} type="button" onClick={() => clear(key)} aria-label={`${label} 기준 해제`}>{label}: {criteria[key]} ×</button>)}</div>}
    {error && <ErrorState title="판단 관계를 불러오지 못했습니다" onRetry={() => void load()}>{error.message}</ErrorState>}
    <div className="jm-versions" data-testid="jm-versions">
      {versionTabs.length === 0
        ? <p className="jm-version-empty" data-testid="jm-version-empty">규칙 버전 데이터가 없습니다. 규칙 ID를 기준으로 탐색하면 버전 탭이 나타납니다.</p>
        : <div role="tablist" aria-label="규칙 버전" className="jm-tabs">
          <button type="button" role="tab" aria-selected={!activeTab} onClick={() => pickVersion(null)}>전체</button>
          {versionTabs.map((tab) => <button key={tab.id} type="button" role="tab" aria-selected={activeTab?.id === tab.id} title={`${tab.ruleId}@${tab.version}`} onClick={() => pickVersion(tab.id)}>v{tab.version}<span className={`jm-vstatus s-${tab.status}`}>{tab.label}</span></button>)}
        </div>}
    </div>
    {loading ? <LoadingState label="판단 관계를 불러오는 중" /> : graph && <div className="jm-layout">
      <div className="jm-board" ref={body} onKeyDown={onKeyDown} data-testid="jm-board" data-node-count={nodes.length} data-edge-count={edges.length}>
        <p className="jm-summary" role="status" data-testid="jm-summary">노드 {nodes.length}개 · 연결 {edges.length}개{graph.truncated && ' · 상한에 도달해 일부만 표시합니다'}</p>
        <ul className="jm-layer-counts" aria-label="계층별 개수">{layers.map((l) => <li key={l.layer} data-testid={`jm-layer-count-${l.layer}`}><span className="mono">{l.count}</span> {l.name}</li>)}</ul>
        {nodes.length === 0 ? <EmptyState title="표시할 판단 관계가 없습니다">선택한 기준에 해당하는 저장된 노드가 없습니다. 기준을 바꾸거나 초기화하세요.</EmptyState> :
          view === 'map'
            ? <MapView expanded={big} items={displayItems} edges={edges} layers={layers} highlight={highlight} tabStop={firstStop} onTabStop={setTabStop} onPick={pick} />
            : <ListView nodes={nodes} edges={edges} layers={layers} highlight={highlight} tabStop={firstStop} onTabStop={setTabStop} onPick={(id) => void select(id)} />}
      </div>
      <Detail node={selectedNode} detail={detail} loading={detailLoading} onPick={(id) => void select(id)} layerName={layerName} />
    </div>}
  </section>;
}
