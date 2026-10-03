import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { GraphEdge, GraphNode, JudgmentGraph } from '../../api/graph';
import { JudgmentMap } from '../JudgmentMap';
import { ruleVersionTabs, versionScope, versionStatusLabel } from './logic';

const mocks = vi.hoisted(() => ({ judgment: vi.fn(), node: vi.fn(), path: vi.fn(), evidence: vi.fn() }));
vi.mock('../../api/graph', () => ({ graphApi: mocks }));

function node(id: string, kind: GraphNode['kind'], layer: number, extra: Partial<GraphNode> = {}): GraphNode {
  return { id, kind, layer, title: id, summary: '', status: null, actor: null, at: null, version: null, source: null, request_id: 'req1', refs: { request_id: 'req1' }, ...extra };
}
const rv = (n: number, status: string) => node(`rv${n}`, 'RuleVersion', 4, { status, version: `R-X-01@${n}`, refs: { rule_id: 'R-X-01', rule_version: `rv${n}` } });
const edge = (type: string, up: string, down: string): GraphEdge => ({ id: `${type}:${down}->${up}`, type, source: down, target: up, upstream: up, downstream: down });
const nodes = [node('c1', 'Correction', 1), node('c2', 'Correction', 1), node('dec1', 'RuleDecision', 3), node('dec2', 'RuleDecision', 3),
  rv(3, 'validating'), rv(1, 'reverted'), rv(2, 'published'), node('s1', 'RunStep', 5), node('s2', 'RunStep', 5), node('lone', 'Correction', 1)];
const edges = [edge('DECIDES', 'c1', 'dec1'), edge('DERIVED_FROM', 'dec1', 'rv1'), edge('APPLIED', 'rv1', 's1'),
  edge('DECIDES', 'c2', 'dec2'), edge('DERIVED_FROM', 'dec2', 'rv2'), edge('APPLIED', 'rv2', 's2')];
const layers = [1, 2, 3, 4, 5].map((layer) => ({ layer, name: `계층${layer}`, desc: '', count: 0 }));
const graph: JudgmentGraph = { nodes, edges, layers, truncated: false, node_count: nodes.length, edge_count: edges.length };

describe('rule version tabs logic', () => {
  it('lists the selected rule versions in order with Korean status labels', () => {
    const tabs = ruleVersionTabs(nodes, 'R-X-01');
    expect(tabs.map((t) => [t.version, t.label])).toEqual([[1, '되돌림'], [2, '운영 중'], [3, '검증 중']]);
    expect(ruleVersionTabs(nodes, 'R-OTHER')).toEqual([]);
    expect(ruleVersionTabs(nodes.filter((n) => n.kind !== 'RuleVersion'), 'R-X-01')).toEqual([]);
    expect(versionStatusLabel('stopped')).toBe('중단');
  });
  it('scopes nodes and edges to what the chosen version is actually connected to', () => {
    const scope = versionScope(edges, 'rv2');
    expect([...scope.nodeIds].sort()).toEqual(['c2', 'dec2', 'rv2', 's2']);
    expect(scope.edgeIds.size).toBe(3);
  });
});

describe('JudgmentMap version tabs and expanded view', () => {
  beforeEach(() => {
    cleanup(); vi.clearAllMocks(); mocks.judgment.mockResolvedValue(graph);
    mocks.node.mockImplementation(async (id: string) => ({ ...nodes.find((n) => n.id === id)!, upstream: [], downstream: [], edges: [], can_read_source: false, source_link: null }));
    mocks.path.mockResolvedValue({ origin: { id: 'x', kind: 'RunStep' }, paths: [], nodes: [], edges: [], upstream_ids: [], downstream_ids: [], truncated: false });
  });
  afterEach(cleanup);
  const page = (query = '?rule_id=R-X-01') => render(<MemoryRouter initialEntries={[`/judgment-map${query}`]}><JudgmentMap /></MemoryRouter>);

  it('filters nodes and links to the selected version and restores them with "전체"', async () => {
    page();
    const summary = await screen.findByTestId('jm-summary');
    expect(summary).toHaveTextContent('노드 10개 · 연결 6개');
    const tabs = screen.getByRole('tablist', { name: '규칙 버전' });
    expect(within(tabs).getAllByRole('tab').map((t) => t.textContent)).toEqual(['전체', 'v1되돌림', 'v2운영 중', 'v3검증 중']);
    fireEvent.click(within(tabs).getByRole('tab', { name: /v2/ }));
    await waitFor(() => expect(screen.getByTestId('jm-summary')).toHaveTextContent('노드 4개 · 연결 3개'));
    expect(within(tabs).getByRole('tab', { name: /v2/ })).toHaveAttribute('aria-selected', 'true');
    fireEvent.click(within(tabs).getByRole('tab', { name: /v3/ }));
    await waitFor(() => expect(screen.getByTestId('jm-summary')).toHaveTextContent('노드 1개 · 연결 0개'));
    fireEvent.click(within(tabs).getByRole('tab', { name: '전체' }));
    await waitFor(() => expect(screen.getByTestId('jm-summary')).toHaveTextContent('노드 10개 · 연결 6개'));
  });
  it('shows an empty version area when no rule version data exists', async () => {
    mocks.judgment.mockResolvedValue({ ...graph, nodes: nodes.filter((n) => n.kind !== 'RuleVersion'), edges: [] });
    page('');
    await screen.findByTestId('jm-summary');
    expect(screen.getByTestId('jm-version-empty')).toHaveTextContent('규칙 버전 데이터가 없습니다');
    expect(screen.queryByRole('tablist', { name: '규칙 버전' })).toBeNull();
  });
  it('toggles the expanded view, keeps focus on the toggle and leaves it with Escape', async () => {
    page();
    await screen.findByTestId('jm-summary');
    const toggle = screen.getByRole('button', { name: '크게 보기' });
    toggle.focus();
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-pressed', 'true');
    expect(document.querySelector('.jm-page')).toHaveClass('is-expanded');
    expect(document.activeElement).toBe(toggle);
    fireEvent.keyDown(toggle, { key: 'Escape' });
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    expect(document.querySelector('.jm-page')).not.toHaveClass('is-expanded');
    expect(document.activeElement).toBe(toggle);
  });
});
