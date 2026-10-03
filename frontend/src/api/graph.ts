import { apiFetch } from './client';

export type GraphKind = 'EvidenceSpan' | 'ModelOutput' | 'Correction' | 'RuleCandidate' | 'RuleDecision' | 'ReviewDecision' | 'RuleVersion' | 'ValidationRun' | 'ConfigVersion' | 'RunStep';
export type GraphNode = {
  id: string; kind: GraphKind; layer: number; title: string; summary: string; status: string | null;
  actor: string | null; at: string | null; version: string | null; source: string | null;
  request_id: string | null; refs: Record<string, string | number | null>;
  upstream_count?: number; downstream_count?: number;
};
export type GraphEdge = { id: string; type: string; source: string; target: string; upstream: string; downstream: string; props?: Record<string, unknown> };
export type GraphLayer = { layer: number; name: string; desc: string; count: number };
export type JudgmentGraph = { nodes: GraphNode[]; edges: GraphEdge[]; layers: GraphLayer[]; truncated: boolean; node_count: number; edge_count: number; criteria?: Record<string, unknown> };
export type GraphCriteria = { request_id?: string; run_id?: string; rule_id?: string; config_version?: string; status?: string };
export type NeighborRef = { id: string; kind: GraphKind; layer: number; title: string };
export type NodeDetail = GraphNode & { upstream: NeighborRef[]; downstream: NeighborRef[]; edges: GraphEdge[]; can_read_source: boolean; source_link: string | null };
export type GraphPath = { direction: 'up' | 'down'; node_ids: string[]; edge_ids: string[] };
export type PathResult = { origin: { id: string; kind: GraphKind }; paths: GraphPath[]; nodes: GraphNode[]; edges: GraphEdge[]; upstream_ids: string[]; downstream_ids: string[]; truncated: boolean };

function query(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => { if (value !== undefined && value !== '') search.set(key, String(value)); });
  const text = search.toString();
  return text ? `?${text}` : '';
}

export const graphApi = {
  judgment: (criteria: GraphCriteria, depth = 6) => apiFetch<JudgmentGraph>(`/api/graph/judgment${query({ ...criteria, depth })}`),
  path: (nodeId: string, kind?: GraphKind, direction: 'up' | 'down' | 'both' = 'both') => apiFetch<PathResult>(`/api/graph/judgment/path${query({ node_id: nodeId, kind, direction })}`),
  node: (nodeId: string, kind?: GraphKind) => apiFetch<NodeDetail>(`/api/graph/judgment/nodes/${encodeURIComponent(nodeId)}${query({ kind })}`),
  evidence: (link: string) => apiFetch<{ source_text?: string; location_json?: string; char_start?: number; char_end?: number }>(link),
};
