import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { NodeDetail, GraphNode } from '../../api/graph';
import { EvidenceViewer, type ViewerTarget } from '../../components/EvidenceViewer';
import { KIND_LABEL } from './logic';
import { statusText } from '../../components/statusLabels';
import { mapNodeTitleLabel } from '../../lib/labels';

type Props = { node: GraphNode | null; detail: NodeDetail | null; loading: boolean; onPick: (id: string) => void; layerName: (layer: number) => string };

export function Detail({ node, detail, loading, onPick, layerName }: Props) {
  const [viewer, setViewer] = useState<ViewerTarget | null>(null);
  if (!node) return <aside className="jm-detail" aria-label="노드 상세"><p className="jm-empty-layer">노드를 선택하면 계층·출처·결정 주체·버전과 상·하류 경로를 보여 줍니다.</p></aside>;
  const data = detail && detail.id === node.id ? detail : null;
  const refs = (data || node).refs;
  const rows: Array<[string, string | null | undefined]> = [
    ['출처', (data || node).source], ['내용', (data || node).summary], ['결정 주체', (data || node).actor],
    ['시각', (data || node).at], ['버전', (data || node).version], ['상태', statusText((data || node).status)],
  ];
  const openSource = () => {
    const { request_id: requestId, revision_id: revision, source, span_id: unitId } = refs;
    if (requestId && revision && source && unitId) setViewer({ requestId: String(requestId), revision: String(revision), source: String(source), unitId: String(unitId), title: `${node.title} · 근거 원문` });
  };
  return <aside className="jm-detail" aria-label="노드 상세" data-testid="jm-detail">
    <div><span className="jm-chip mono">{node.layer}계층 · {layerName(node.layer)}</span> <span className={`jm-chip kind k-${node.kind}`}>{KIND_LABEL[node.kind] || node.kind}</span></div>
    <h2>{mapNodeTitleLabel(node.title)}</h2>
    <p className="jm-id mono">{node.id}</p>
    <dl>{rows.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value || '—'}</dd></div>)}</dl>
    {loading && !data && <p role="status">상세를 불러오는 중…</p>}
    {data && <div className="jm-trace">
      <h3 data-testid="jm-up-count">↑ 근거 쪽으로 {data.upstream_count ?? 0}개</h3>
      <div className="jm-chips">{data.upstream.map((n) => <button key={n.id} type="button" onClick={() => onPick(n.id)}>{KIND_LABEL[n.kind]} · {mapNodeTitleLabel(n.title)}</button>)}</div>
      <h3 data-testid="jm-down-count">↓ 실행 쪽으로 {data.downstream_count ?? 0}개</h3>
      <div className="jm-chips">{data.downstream.map((n) => <button key={n.id} type="button" onClick={() => onPick(n.id)}>{KIND_LABEL[n.kind]} · {mapNodeTitleLabel(n.title)}</button>)}</div>
    </div>}
    <div className="jm-links">
      {node.kind === 'EvidenceSpan' && refs.span_id && refs.source && refs.revision_id && <button type="button" onClick={openSource}>원문 열기</button>}
      {node.kind === 'EvidenceSpan' && data && !data.source_link && <span className="jm-note">원문 텍스트는 원문 열람 권한이 있는 계정에서만 보입니다. 위치는 열 수 있습니다.</span>}
      {refs.request_id && <Link to={`/review?request_id=${encodeURIComponent(String(refs.request_id))}`}>원문·검토 열기</Link>}
      {refs.run_id && <Link to={`/observatory?run_id=${encodeURIComponent(String(refs.run_id))}`}>Flow에서 보기</Link>}
      {(refs.rule_version || refs.candidate_id || refs.config_version) && <Link className="primary" to={refs.rule_version ? `/learning?rule_id=${encodeURIComponent(String(refs.rule_version))}` : refs.candidate_id ? `/learning?candidate_id=${encodeURIComponent(String(refs.candidate_id))}` : `/learning?config_version=${encodeURIComponent(String(refs.config_version))}`}>규칙 학습에서 보기</Link>}
    </div>
    <EvidenceViewer target={viewer} onClose={() => setViewer(null)} />
    <p className="jm-note">요청·실행·판단·규칙 버전 ID는 Flow·Topology·규칙 학습 화면과 같습니다.</p>
  </aside>;
}
