import { afterEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { GraphNode } from '../../api/graph';
import { Detail } from './Detail';
import { MapView } from './MapView';
import { SCENE, buildDisplay, computeHighlight, edgeAnchors, edgePath, layoutScene, tileTitle, versionChips, versionSummary } from './logic';

afterEach(cleanup);
const node = (id: string, kind: GraphNode['kind'], layer: number, title = id, extra: Partial<GraphNode> = {}): GraphNode =>
  ({ id, kind, layer, title, summary: '', status: null, actor: null, at: null, version: null, source: null, request_id: 'r', refs: {}, ...extra });
const layers = [1, 2, 3, 4, 5].map((layer) => ({ layer, name: `계층${layer}`, desc: `설명${layer}`, count: 0 }));

describe('tile titles', () => {
  it('drops the repeated kind label and Jev prefix but never returns an empty title', () => {
    expect(tileTitle('EvidenceSpan', '문서 근거 회의실.md 3 3')).toBe('회의실.md 3 3');
    expect(tileTitle('ModelOutput', 'Jev · lead_org')).toBe('담당 조직 · 주관');
    expect(tileTitle('ModelOutput', 'Jev 반환값')).toBe('Jev 반환값');
    expect(tileTitle('RunStep', '실행 단계')).toBe('실행 단계');
  });
});

describe('version chips and summary', () => {
  it('splits the run-step versions JSON into labelled chips instead of raw JSON', () => {
    expect(versionChips('{"config_version":1,"model":"jev-1.13.0","question_set_version":2}')).toEqual(['config v1', 'model jev-1.13.0', 'qset v2']);
    expect(versionChips('{"config_version":1,"config":1,"model":"jev-1.13.0"}')).toEqual(['config v1', 'model jev-1.13.0']);
    expect(versionChips('config v3')).toEqual(['config v3']);
    expect(versionChips('rev_84081695e36c440f86babf41a20e619d')).toEqual(['rev_8408…']);
    expect(versionChips(null)).toEqual([]);
  });
  it('summarises versions from real node data only', () => {
    const tabs = [{ id: 'a', ruleId: 'R', version: 1, status: 'published', label: '운영 중' }, { id: 'b', ruleId: 'R', version: 2, status: 'validating', label: '검증 중' }];
    expect(versionSummary(tabs, null, 7, 5)).toContain('v1 운영 중');
    expect(versionSummary(tabs, tabs[1], 3, 2, '검증 요약')).toBe('v2 · 검증 중 — 검증 요약');
    expect(versionSummary(tabs, tabs[1], 3, 2)).toContain('노드 3개');
  });
});

describe('funnel layout', () => {
  const items = buildDisplay([node('e', 'EvidenceSpan', 1), node('s', 'RunStep', 5)], new Set(), new Set());
  const scene = layoutScene(items);
  it('narrows the slabs from top to bottom and keeps empty layers thin', () => {
    const widths = scene.planes.map((p) => p.w);
    expect([...widths].sort((a, b) => b - a)).toEqual(widths);
    expect(new Set(widths).size).toBe(5);
    const empty = scene.planes.find((p) => p.layer === 3)!, filled = scene.planes.find((p) => p.layer === 1)!;
    expect(empty.h).toBeLessThan(filled.h);
    expect(empty.h).toBeLessThanOrEqual(80);
  });
  it('places tiles inside their own slab and draws links between real tile anchors', () => {
    const a = scene.boxes.get('e')!, b = scene.boxes.get('s')!;
    expect(b.y).toBeGreaterThan(a.y);
    const [from, to] = [edgeAnchors(a, 'bottom'), edgeAnchors(b, 'top')];
    expect(from.y).toBe(a.y + a.h);
    expect(to.y).toBe(b.y);
    const d = edgePath(a, b);
    expect(d.startsWith(`M${from.x} ${from.y}`)).toBe(true);
    expect(d.endsWith(`${to.x} ${to.y}`)).toBe(true);
    // every coordinate stays inside the scene so no line converges to an off-screen point
    for (const n of d.match(/-?\d+(\.\d+)?/g)!.map(Number)) { expect(n).toBeGreaterThan(-5); expect(n).toBeLessThan(Math.max(SCENE.width, scene.height) + 5); }
  });
});

describe('stage rendering', () => {
  const nodes = [node('e1', 'EvidenceSpan', 1, '문서 근거 아주아주 긴 파일 이름이 들어가는 제목입니다 2 5'), node('s1', 'RunStep', 5, '실행 단계')];
  const edges = [{ id: 'x', type: 'USED_OUTPUT', source: 's1', target: 'e1', upstream: 'e1', downstream: 's1' }];
  const draw = (selected: string | null = null) => {
    const items = buildDisplay(nodes, new Set(), new Set());
    return render(<MapView items={items} edges={edges} layers={layers.map((l) => ({ ...l, count: l.layer === 1 || l.layer === 5 ? 1 : 0 }))} highlight={computeHighlight(edges, selected)} tabStop="e1" onTabStop={() => undefined} onPick={() => undefined} />);
  };
  it('shows the kind as a small chip, the short title with the full title on hover, and per-layer counts', () => {
    draw();
    const tile = document.querySelector('[data-node-id="e1"]') as HTMLElement;
    expect(within(tile).getByText('문서 근거')).toHaveClass('jm-chip');
    expect(tile).toHaveAttribute('title', nodes[0].title);
    expect(tile.getAttribute('aria-label')).toContain(nodes[0].title);
    expect(tile.querySelector('.jm-t')!.textContent).not.toMatch(/^문서 근거/);
    expect(document.querySelectorAll('.jm-plane')).toHaveLength(5);
    expect(document.querySelector('.jm-plane[data-layer="1"] .jm-plane-num')).toHaveTextContent('1');
    expect(document.querySelector('.jm-plane[data-layer="3"]')).toHaveClass('is-empty');
    expect(screen.getAllByText('이 기준에 해당하는 노드가 없습니다.')).toHaveLength(3);
  });
  it('marks the selected tile and its path, dims the rest and draws the path line', () => {
    draw('s1');
    expect(document.querySelector('[data-node-id="s1"]')).toHaveClass('is-selected');
    expect(document.querySelector('[data-node-id="e1"]')).toHaveClass('is-path');
    expect(document.querySelector('.jm-line.is-path')).toBeInTheDocument();
  });
});

describe('detail panel formatting', () => {
  const step = node('step_0a1b2c3d4e5f60718293a4b5c6d7e8f9', 'RunStep', 5, '실행 단계', { status: 'completed', at: '2026-10-04T10:07:52.540000000+00:00', version: '{"config_version":1,"model":"jev-1.13.0","question_set_version":2}' });
  const info = { ...step, upstream: [{ id: 'u1', kind: 'ModelOutput' as const, layer: 1, title: 'Jev · lead_org' }], downstream: [], edges: [], can_read_source: false, source_link: null };
  const show = () => render(<MemoryRouter><Detail node={step} detail={info} loading={false} onPick={() => undefined} layerName={() => '업무 단계'} /></MemoryRouter>);
  it('shows versions as chips, a short id with copy, a formatted time and a Korean status badge', () => {
    show();
    const panel = screen.getByTestId('jm-detail');
    for (const chip of ['config v1', 'model jev-1.13.0', 'qset v2']) expect(within(panel).getByText(chip)).toHaveClass('jm-vchip');
    expect(panel.textContent).not.toContain('"config_version"');
    expect(within(panel).getByTestId('jm-short-id')).toHaveTextContent('step_0a1…');
    expect(within(panel).getByTestId('jm-short-id')).toHaveAttribute('title', step.id);
    expect(within(panel).getByRole('button', { name: 'ID 복사' })).toBeInTheDocument();
    expect(panel.textContent).not.toContain('2026-10-04T10:07:52.540000000');
    expect(panel.textContent).not.toContain(step.id);
    expect(within(panel).getByText('완료')).toHaveClass('jm-badge');
    expect(within(panel).getByRole('button', { name: /담당 조직/ })).toHaveClass('l-1');
  });
  it('copies the full id', () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    show();
    fireEvent.click(screen.getByRole('button', { name: 'ID 복사' }));
    expect(writeText).toHaveBeenCalledWith(step.id);
  });
});
