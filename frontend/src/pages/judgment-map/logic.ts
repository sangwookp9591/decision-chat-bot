import type { GraphEdge, GraphNode } from '../../api/graph';
import { statusText } from '../../components/statusLabels';
import { mapNodeTitleLabel } from '../../lib/labels';
import { AI_NAME } from '../../lib/brand';

export type Highlight = { selected: string | null; nodeIds: Set<string>; edgeIds: Set<string>; upstreamIds: Set<string>; downstreamIds: Set<string> };

/** Monotonic closure from the selected node along stored edges (upstream = toward evidence). */
export function computeHighlight(edges: GraphEdge[], selected: string | null): Highlight {
  const result: Highlight = { selected, nodeIds: new Set(), edgeIds: new Set(), upstreamIds: new Set(), downstreamIds: new Set() };
  if (!selected) return result;
  result.nodeIds.add(selected);
  const walk = (from: 'downstream' | 'upstream', to: 'upstream' | 'downstream', sink: Set<string>) => {
    const queue = [selected];
    while (queue.length) {
      const current = queue.shift() as string;
      for (const edge of edges) {
        if (edge[from] !== current) continue;
        result.edgeIds.add(edge.id);
        const next = edge[to];
        if (!sink.has(next)) { sink.add(next); result.nodeIds.add(next); queue.push(next); }
      }
    }
  };
  walk('downstream', 'upstream', result.upstreamIds);
  walk('upstream', 'downstream', result.downstreamIds);
  return result;
}

const VERSION_STATUS: Record<string, string> = { published: '운영 중', active: '운영 중', validating: '검증 중', validated: '검증 중', stopped: '중단', reverted: '되돌림' };
export const versionStatusLabel = (status: string | null | undefined) => (status ? VERSION_STATUS[status] || statusText(status) : '상태 없음');

export type VersionTab = { id: string; ruleId: string; version: number; status: string | null; label: string };

/** Versions of one rule found among the loaded RuleVersion nodes (ascending); [] when there is no version data. */
export function ruleVersionTabs(nodes: GraphNode[], ruleId: string | null): VersionTab[] {
  if (!ruleId) return [];
  return nodes.filter((node) => node.kind === 'RuleVersion' && node.refs.rule_id === ruleId)
    .map((node) => ({ id: node.id, ruleId, version: Number(String(node.version || '').split('@')[1] ?? NaN), status: node.status, label: versionStatusLabel(node.status) }))
    .filter((tab) => Number.isFinite(tab.version)).sort((a, b) => a.version - b.version);
}

/** Rule whose versions to show: the criteria rule, else the only rule among the loaded version nodes. */
export function tabRuleId(nodes: GraphNode[], criteriaRule?: string): string | null {
  if (criteriaRule) return criteriaRule.split('@')[0];
  const rules = new Set(nodes.filter((node) => node.kind === 'RuleVersion').map((node) => String(node.refs.rule_id || '')).filter(Boolean));
  return rules.size === 1 ? [...rules][0] : null;
}

/** Nodes and links that one rule version is connected to (monotonic closure both ways); sibling versions drop out. */
export function versionScope(edges: GraphEdge[], versionNodeId: string) {
  const { nodeIds, edgeIds } = computeHighlight(edges, versionNodeId);
  return { nodeIds, edgeIds };
}

export type DisplayItem = { id: string; layer: number; kind: string; label: string; nodes: GraphNode[]; group: boolean };
export const COLLAPSE_LIMIT = 12;

/** Collapse a crowded layer into one bundle per kind; kept ids (selection/path) always stay visible. */
export function buildDisplay(nodes: GraphNode[], expanded: Set<string>, keep: Set<string>, limit = COLLAPSE_LIMIT): DisplayItem[] {
  const out: DisplayItem[] = [];
  for (const layer of [1, 2, 3, 4, 5]) {
    const inLayer = nodes.filter((node) => node.layer === layer);
    if (inLayer.length <= limit) { inLayer.forEach((node) => out.push(single(node))); continue; }
    const byKind = new Map<string, GraphNode[]>();
    inLayer.forEach((node) => byKind.set(node.kind, [...(byKind.get(node.kind) || []), node]));
    for (const [kind, members] of byKind) {
      const groupId = `group:${layer}:${kind}`;
      if (members.length <= 3 || expanded.has(groupId)) { members.forEach((node) => out.push(single(node))); continue; }
      const shown = members.filter((node) => keep.has(node.id));
      shown.forEach((node) => out.push(single(node)));
      const hidden = members.filter((node) => !keep.has(node.id));
      if (hidden.length) out.push({ id: groupId, layer, kind, label: `+${hidden.length}개`, nodes: hidden, group: true });
    }
  }
  return out;
}

function single(node: GraphNode): DisplayItem { return { id: node.id, layer: node.layer, kind: node.kind, label: mapNodeTitleLabel(node.title), nodes: [node], group: false }; }

/** Move focus between display items: left/right inside a layer, up/down to the nearest index in another layer. */
export function neighborId(items: DisplayItem[], current: string, key: string): string | null {
  const layers = [1, 2, 3, 4, 5].map((layer) => items.filter((item) => item.layer === layer)).filter((list) => list.length);
  const row = layers.findIndex((list) => list.some((item) => item.id === current));
  if (row < 0) return layers[0]?.[0]?.id ?? null;
  const index = layers[row].findIndex((item) => item.id === current);
  if (key === 'ArrowRight') return layers[row][Math.min(index + 1, layers[row].length - 1)].id;
  if (key === 'ArrowLeft') return layers[row][Math.max(index - 1, 0)].id;
  if (key === 'ArrowDown' || key === 'ArrowUp') {
    const target = layers[Math.max(0, Math.min(layers.length - 1, row + (key === 'ArrowDown' ? 1 : -1)))];
    const ratio = layers[row].length > 1 ? index / (layers[row].length - 1) : 0;
    return target[Math.round(ratio * (target.length - 1))].id;
  }
  if (key === 'Home') return layers[row][0].id;
  if (key === 'End') return layers[row][layers[row].length - 1].id;
  return null;
}

export function mergeGraph<T extends { id: string }>(base: T[], extra: T[]): T[] {
  const seen = new Set(base.map((item) => item.id));
  return [...base, ...extra.filter((item) => !seen.has(item.id))];
}

export function pathRows(nodes: GraphNode[], edges: GraphEdge[], highlight: Highlight) {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  return edges.filter((edge) => highlight.edgeIds.has(edge.id)).map((edge) => ({
    id: edge.id, type: edge.type, upstream: byId.get(edge.upstream), downstream: byId.get(edge.downstream),
    outcome: typeof edge.props?.outcome === 'string' ? edge.props.outcome : null,
  }));
}

export const KIND_LABEL: Record<string, string> = {
  EvidenceSpan: '문서 근거', ModelOutput: `${AI_NAME} 반환값`, Correction: '사람 수정', RuleCandidate: '규칙 후보',
  RuleDecision: '규칙 결정', ReviewDecision: '요청 검토 결정', RuleVersion: '규칙 버전', ValidationRun: '비교 검증',
  ConfigVersion: 'Config 버전', RunStep: '실행 단계',
};
export const RELATION_LABEL: Record<string, string> = {
  CITES: '인용', CORRECTS: '수정', RECORDED: '기록', SUPPORTED_BY: '지지·반례', DECIDES: '결정', DERIVED_FROM: '파생',
  PUBLISHED_IN: '게시', VALIDATES: '검증', APPLIED: '적용', USED_OUTPUT: '반환값 사용',
};

export const SCENE = { width: 960, nodeW: 164, nodeH: 58, gap: 14, pad: 24, label: 56, emptyH: 76, planeGap: 52, skew: -22 };
/** Slab widths narrow from evidence (top) to work step (bottom): the funnel. */
export const PLANE_WIDTHS = [920, 820, 720, 620, 520];
export const SKEW_T = Math.tan((SCENE.skew * Math.PI) / 180);
export type Box = { x: number; y: number; w: number; h: number };
export type Plane = Box & { layer: number };

/** Short tile title: the kind is shown as a chip, so a repeated kind label / "Decision AI ·" prefix is dropped (never to an empty title). */
export function tileTitle(kind: string, title: string): string {
  const full = mapNodeTitleLabel(title);
  const kindLabel = KIND_LABEL[kind] || '';
  const aiPrefix = new RegExp(`^${AI_NAME.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*[·:]\\s*`);
  let text = full.replace(aiPrefix, '');
  if (kindLabel && text.startsWith(kindLabel)) text = text.slice(kindLabel.length).replace(/^\s*[·:]?\s*/, '');
  return text.trim() || full;
}

const VERSION_KEY: Record<string, string> = { config_version: 'config', config: 'config', model: 'model', model_version: 'model', question_set_version: 'qset', qset_version: 'qset', rule_version: 'rule' };
const shortId = (value: string) => (value.length > 12 && /^[a-z]+_[0-9a-f]{8,}/i.test(value) ? `${value.slice(0, 8)}…` : value);

/** Version strings come as plain text or as the run step's raw JSON; show them as short chips. */
export function versionChips(version: string | null | undefined): string[] {
  const text = String(version ?? '').trim();
  if (!text || /^[—–-]$/.test(text) || text === '{}') return [];
  if (text.startsWith('{')) {
    try {
      const parsed = JSON.parse(text) as Record<string, unknown>;
      // Aliases (config / config_version) can carry the same value; one chip per label+value.
      return [...new Set(Object.entries(parsed).filter(([, value]) => value !== null && value !== undefined && typeof value !== 'object').map(([key, value]) => {
        const label = VERSION_KEY[key] || key.replace(/_version$/, '');
        const raw = String(value);
        return `${label} ${/^\d+$/.test(raw) ? `v${raw}` : raw}`;
      }))];
    } catch { return [text]; }
  }
  return [shortId(text)];
}

/** One-sentence change summary of the shown version, from stored node data only. */
export function versionSummary(tabs: VersionTab[], active: VersionTab | null, nodeCount: number, edgeCount: number, nodeSummary = ''): string {
  if (active) return `v${active.version} · ${active.label} — ${nodeSummary || `연결된 노드 ${nodeCount}개 · 연결 ${edgeCount}개`}`;
  if (!tabs.length) return '';
  const live = tabs.find((tab) => tab.status === 'published' || tab.status === 'active'), testing = tabs.find((tab) => tab.status === 'validating' || tab.status === 'validated');
  return [`규칙 v${tabs[0].version}–v${tabs[tabs.length - 1].version}`, live && `v${live.version} 운영 중`, testing && `v${testing.version} 검증 중`].filter(Boolean).join(' · ');
}

/** Slab layout: one thin or tall slab per layer, tiles centred per row; x already includes the slab skew so SVG links meet the tiles. */
export function layoutScene(items: DisplayItem[]) {
  const { width, nodeW, nodeH, gap, pad, label, emptyH, planeGap } = SCENE;
  const boxes = new Map<string, Box>();
  const planes: Plane[] = [];
  let y = 0;
  [1, 2, 3, 4, 5].forEach((layer, index) => {
    const pw = PLANE_WIDTHS[index], px = (width - pw) / 2;
    const list = items.filter((item) => item.layer === layer);
    const columns = Math.max(1, Math.floor((pw - 2 * pad + gap) / (nodeW + gap)));
    const rows = Math.ceil(list.length / columns);
    const height = list.length ? pad + rows * nodeH + (rows - 1) * gap + label : emptyH;
    planes.push({ layer, x: px, y, w: pw, h: height });
    const cy = y + height / 2;
    list.forEach((item, i) => {
      const row = Math.floor(i / columns), inRow = Math.min(columns, list.length - row * columns), col = i % columns;
      const rowW = inRow * nodeW + (inRow - 1) * gap;
      const ty = y + pad + row * (nodeH + gap);
      boxes.set(item.id, { x: px + (pw - rowW) / 2 + col * (nodeW + gap) + SKEW_T * (ty + nodeH / 2 - cy), y: ty, w: nodeW, h: nodeH });
    });
    y += height + planeGap;
  });
  return { boxes, planes, width, height: y - planeGap };
}

/** Top / bottom edge midpoint of a skewed tile (the parallelogram edge, not the unskewed box). */
export function edgeAnchors(box: Box, side: 'top' | 'bottom') {
  return side === 'bottom' ? { x: Math.round(box.x + box.w / 2 + (SKEW_T * box.h) / 2), y: box.y + box.h } : { x: Math.round(box.x + box.w / 2 - (SKEW_T * box.h) / 2), y: box.y };
}

/** Thin curve between the facing tile edges; same-row links bow downward. */
export function edgePath(from: Box, to: Box): string {
  if (Math.abs(from.y - to.y) < 1) {
    const a = edgeAnchors(from, 'bottom'), b = edgeAnchors(to, 'bottom'), bow = 22;
    return `M${a.x} ${a.y} C${a.x} ${a.y + bow},${b.x} ${b.y + bow},${b.x} ${b.y}`;
  }
  const down = from.y < to.y;
  const a = edgeAnchors(from, down ? 'bottom' : 'top'), b = edgeAnchors(to, down ? 'top' : 'bottom'), mid = (a.y + b.y) / 2;
  return `M${a.x} ${a.y} C${a.x} ${mid},${b.x} ${mid},${b.x} ${b.y}`;
}

/** Map every underlying edge onto the (possibly bundled) display items and de-duplicate. */
export function displayEdges(items: DisplayItem[], edges: GraphEdge[]) {
  const owner = new Map<string, string>();
  items.forEach((item) => item.nodes.forEach((node) => owner.set(node.id, item.id)));
  const merged = new Map<string, { id: string; from: string; to: string; edges: GraphEdge[] }>();
  for (const edge of edges) {
    const from = owner.get(edge.upstream), to = owner.get(edge.downstream);
    if (!from || !to || from === to) continue;
    const key = `${from}>${to}`;
    const entry = merged.get(key) || { id: key, from, to, edges: [] };
    entry.edges.push(edge);
    merged.set(key, entry);
  }
  return [...merged.values()];
}
