import type { GraphEdge, GraphLayer, GraphNode } from '../../api/graph';
import { KIND_LABEL, RELATION_LABEL, pathRows, type Highlight } from './logic';

type Props = {
  nodes: GraphNode[]; edges: GraphEdge[]; layers: GraphLayer[]; highlight: Highlight;
  tabStop: string | null; onTabStop: (id: string) => void; onPick: (id: string) => void;
};

export function ListView({ nodes, edges, layers, highlight, tabStop, onTabStop, onPick }: Props) {
  const rows = pathRows(nodes, edges, highlight);
  const role = (id: string) => highlight.selected === id ? '선택' : highlight.upstreamIds.has(id) ? '근거 쪽' : highlight.downstreamIds.has(id) ? '실행 쪽' : '';
  return <div className="jm-list" data-testid="jm-list">
    {layers.map((layer) => {
      const list = nodes.filter((node) => node.layer === layer.layer);
      return <section key={layer.layer} aria-labelledby={`jm-layer-${layer.layer}`}>
        <h2 id={`jm-layer-${layer.layer}`}><span className="mono">{list.length}</span> {layer.layer}. {layer.name} <small>· {layer.desc}</small></h2>
        {list.length === 0 ? <p className="jm-empty-layer">이 기준에 해당하는 노드가 없습니다.</p> :
          <ul>{list.map((node) => <li key={node.id}><button type="button" data-node-id={node.id} data-kind={node.kind}
            className={`jm-item ${highlight.selected === node.id ? 'is-selected' : highlight.nodeIds.has(node.id) ? 'is-path' : highlight.selected ? 'is-dim' : ''}`}
            aria-pressed={highlight.selected === node.id} tabIndex={tabStop === node.id ? 0 : -1}
            onFocus={() => onTabStop(node.id)} onClick={() => onPick(node.id)}>
            <small>{KIND_LABEL[node.kind] || node.kind}{role(node.id) ? ` · ${role(node.id)}` : ''}</small>{node.title}
          </button></li>)}</ul>}
      </section>;
    })}
    <section aria-labelledby="jm-path-table">
      <h2 id="jm-path-table">선택 경로 표</h2>
      {!highlight.selected ? <p className="jm-empty-layer">노드를 선택하면 근거 쪽·실행 쪽으로 이어지는 저장된 관계를 표로 보여 줍니다.</p> :
        rows.length === 0 ? <p className="jm-empty-layer">선택한 노드에 저장된 연결이 없습니다.</p> :
        <div className="table-scroll"><table><caption>선택한 노드의 상·하류 경로 (저장된 관계)</caption>
          <thead><tr><th scope="col">근거 쪽 노드</th><th scope="col">관계</th><th scope="col">실행 쪽 노드</th><th scope="col">비고</th></tr></thead>
          <tbody>{rows.map((row) => <tr key={row.id}><td>{row.upstream ? `${row.upstream.layer}계층 ${KIND_LABEL[row.upstream.kind]} ${row.upstream.title}` : '—'}</td><td>{RELATION_LABEL[row.type] || row.type}</td><td>{row.downstream ? `${row.downstream.layer}계층 ${KIND_LABEL[row.downstream.kind]} ${row.downstream.title}` : '—'}</td><td>{row.outcome ? ({ used: '규칙 사용', out_of_scope: '범위 밖 · 미사용', conflict: '충돌 · 미적용' } as Record<string, string>)[row.outcome] || row.outcome : ''}</td></tr>)}</tbody>
        </table></div>}
    </section>
  </div>;
}
