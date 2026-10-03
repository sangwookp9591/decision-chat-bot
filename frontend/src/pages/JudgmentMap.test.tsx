import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { GraphEdge, GraphNode, JudgmentGraph } from '../api/graph';
import { JudgmentMap } from './JudgmentMap';
import { buildDisplay, computeHighlight, displayEdges, layoutScene, neighborId } from './judgment-map/logic';

const mocks = vi.hoisted(() => ({ judgment: vi.fn(), node: vi.fn(), path: vi.fn(), evidence: vi.fn() }));
vi.mock('../api/graph', () => ({ graphApi: mocks }));

function node(id: string, kind: GraphNode['kind'], layer: number, title = id): GraphNode {
  return { id, kind, layer, title, summary: `${title} 요약`, status: null, actor: null, at: null, version: null, source: null, request_id: 'req1', refs: { request_id: 'req1' } };
}
function edge(type: string, up: string, down: string, source = down, target = up): GraphEdge {
  return { id: `${type}:${source}->${target}`, type, source, target, upstream: up, downstream: down };
}
const N = { es: node('es1', 'EvidenceSpan', 1), mo: node('mo1', 'ModelOutput', 1), co: node('c1', 'Correction', 1), cand: node('cand1', 'RuleCandidate', 2),
  dec: node('dec1', 'RuleDecision', 3), rv: node('rv1', 'RuleVersion', 4), step: node('step1', 'RunStep', 5), lone: node('lone', 'Correction', 1) };
const E = [edge('CITES', 'es1', 'mo1'), edge('CORRECTS', 'mo1', 'c1'), edge('SUPPORTED_BY', 'c1', 'cand1'), edge('DECIDES', 'cand1', 'dec1'),
  edge('DERIVED_FROM', 'dec1', 'rv1'), edge('APPLIED', 'rv1', 'step1')];
const layers = [1, 2, 3, 4, 5].map((layer) => ({ layer, name: `계층${layer}`, desc: '설명', count: 0 }));
const graph: JudgmentGraph = { nodes: Object.values(N), edges: E, layers, truncated: false, node_count: 8, edge_count: 6 };

beforeEach(() => {
  cleanup(); vi.clearAllMocks();
  mocks.judgment.mockResolvedValue(graph);
  mocks.node.mockImplementation(async (id: string) => ({ ...Object.values(N).find((n) => n.id === id)!, upstream: [], downstream: [], edges: [], upstream_count: 3, downstream_count: 2, can_read_source: false, source_link: null }));
  mocks.path.mockResolvedValue({ origin: { id: 'x', kind: 'RunStep' }, paths: [], nodes: [], edges: [], upstream_ids: [], downstream_ids: [], truncated: false });
});
afterEach(cleanup);

describe('path highlight', () => {
  it('follows only stored edges toward evidence and toward execution', () => {
    const h = computeHighlight(E, 'c1');
    expect([...h.upstreamIds].sort()).toEqual(['es1', 'mo1']);
    expect([...h.downstreamIds].sort()).toEqual(['cand1', 'dec1', 'rv1', 'step1']);
    expect(h.nodeIds.has('lone')).toBe(false);
    expect(h.edgeIds.size).toBe(6);
    expect(computeHighlight(E, null).nodeIds.size).toBe(0);
  });
  it('does not connect nodes across a missing relationship', () => {
    const h = computeHighlight(E.filter((e) => e.type !== 'DECIDES'), 'step1');
    expect([...h.upstreamIds].sort()).toEqual(['dec1', 'rv1']);
    expect(h.upstreamIds.has('cand1')).toBe(false);
  });
});

describe('display helpers', () => {
  it('bundles crowded layers by kind but keeps path members visible', () => {
    const many = Array.from({ length: 14 }, (_, i) => node(`mo${i}`, 'ModelOutput', 1));
    const items = buildDisplay(many, new Set(), new Set(['mo3']));
    expect(items.filter((i) => i.group).map((i) => [i.label, i.nodes.length])).toEqual([['ModelOutput 외 13개', 13]]);
    expect(items.some((i) => i.id === 'mo3')).toBe(true);
    expect(buildDisplay(many, new Set(['group:1:ModelOutput']), new Set()).length).toBe(14);
    expect(displayEdges(items, [edge('CITES', 'mo6', 'mo7')])).toEqual([]); // both ends bundled together: no self link
    expect(displayEdges(items, [edge('CITES', 'mo3', 'mo5')]).map((l) => [l.from, l.to])).toEqual([['mo3', 'group:1:ModelOutput']]);
  });
  it('lays out one plane per layer and moves focus with arrows', () => {
    const items = buildDisplay(Object.values(N), new Set(), new Set());
    expect(layoutScene(items).planes).toHaveLength(5);
    expect(neighborId(items, 'es1', 'ArrowRight')).toBe('mo1');
    expect(neighborId(items, 'mo1', 'ArrowLeft')).toBe('es1');
    expect(neighborId(items, 'es1', 'ArrowDown')).toBe('cand1');
    expect(neighborId(items, 'cand1', 'ArrowUp')).toBe('es1');
  });
});

describe('JudgmentMap list view', () => {
  const renderPage = () => render(<MemoryRouter initialEntries={['/judgment-map?rule_id=R-X-01']}><JudgmentMap /></MemoryRouter>);
  it('renders counts, every node in layer lists and an empty-layer state', async () => {
    mocks.judgment.mockResolvedValue({ ...graph, nodes: graph.nodes.filter((n) => n.layer !== 3), edges: [] });
    renderPage();
    expect(await screen.findByTestId('jm-summary')).toHaveTextContent('노드 7개 · 연결 0개');
    fireEvent.click(screen.getByRole('button', { name: '목록 보기' }));
    const list = screen.getByTestId('jm-list');
    expect(within(list).getAllByRole('button', { name: /문서 근거|Jev 반환값|사람 수정/ })).toHaveLength(4);
    expect(within(list).getByText('이 기준에 해당하는 노드가 없습니다.')).toBeInTheDocument();
    expect(mocks.judgment).toHaveBeenCalledWith({ request_id: undefined, run_id: undefined, rule_id: 'R-X-01', config_version: undefined, status: undefined });
  });
  it('localizes internal field and decision codes in ordinary node titles', async () => {
    mocks.judgment.mockResolvedValue({ ...graph, nodes: [node('n1', 'ModelOutput', 1, 'Jev · lead_org'), node('n2', 'RuleDecision', 3, '검토 결정 · request_info')] });
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: '목록 보기' }));
    const list = screen.getByTestId('jm-list');
    expect(within(list).getByText('Jev · 담당 조직 · 주관')).toBeInTheDocument();
    expect(within(list).getByText('검토 결정 · 정보 요청')).toBeInTheDocument();
    expect(within(list).queryByText('Jev · lead_org')).not.toBeInTheDocument();
  });
  it('selects with Enter, shows detail counts and the path table, clears with Escape', async () => {
    renderPage();
    await screen.findByTestId('jm-summary');
    fireEvent.click(screen.getByRole('button', { name: '목록 보기' }));
    const target = within(screen.getByTestId('jm-list')).getByRole('button', { name: /dec1/ });
    target.focus();
    fireEvent.keyDown(target, { key: 'ArrowUp' });
    await waitFor(() => expect(document.activeElement?.getAttribute('data-node-id')).toBe('cand1'));
    fireEvent.click(target);
    expect(await screen.findByTestId('jm-up-count')).toHaveTextContent('↑ 근거 쪽으로 3개');
    expect(screen.getByTestId('jm-down-count')).toHaveTextContent('↓ 실행 쪽으로 2개');
    expect(mocks.path).toHaveBeenCalledWith('dec1', 'RuleDecision', 'both');
    const table = screen.getByRole('table');
    expect(within(table).getAllByRole('row')).toHaveLength(1 + 6);
    fireEvent.keyDown(screen.getByTestId('jm-board'), { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('jm-up-count')).toBeNull());
  });
});
