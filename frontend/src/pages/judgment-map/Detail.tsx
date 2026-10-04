import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { NodeDetail, GraphNode } from '../../api/graph';
import { EvidenceViewer, type ViewerTarget } from '../../components/EvidenceViewer';
import { KIND_LABEL, tileTitle, versionChips } from './logic';
import { formatTime } from '../../lib/format';
import { statusText } from '../../components/statusLabels';
import { mapNodeTitleLabel } from '../../lib/labels';

type Props = { node: GraphNode | null; detail: NodeDetail | null; loading: boolean; onPick: (id: string) => void; layerName: (layer: number) => string };

export function Detail({ node, detail, loading, onPick, layerName }: Props) {
  const [viewer, setViewer] = useState<ViewerTarget | null>(null);
  const [copied, setCopied] = useState(false);
  if (!node) return <aside className="jm-detail" aria-label="노드 상세"><p className="jm-empty-layer">노드를 선택하면 계층·출처·결정 주체·버전과 상·하류 경로를 보여 줍니다.</p></aside>;
  const data = detail && detail.id === node.id ? detail : null;
  const refs = (data || node).refs;
  const shown = data || node;
  const chips = versionChips(shown.version);
  const rows: Array<[string, ReactNode]> = [
    ['출처', shown.source], ['내용', shown.summary], ['결정 주체', shown.actor],
    ['시각', shown.at ? <time dateTime={shown.at}>{formatTime(shown.at)}</time> : null],
    ['버전', chips.length ? <span className="jm-vchips">{chips.map((chip) => <span key={chip} className="jm-vchip mono">{chip}</span>)}</span> : null],
    ['상태', shown.status ? <span className={`jm-badge s-${shown.status}`}>{statusText(shown.status)}</span> : null],
  ];
  const copy = () => { try { void navigator.clipboard?.writeText(node.id).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); }).catch(() => undefined); } catch { /* clipboard unavailable */ } };
  const openSource = () => {
    const { request_id: requestId, revision_id: revision, source, span_id: unitId } = refs;
    if (requestId && revision && source && unitId) setViewer({ requestId: String(requestId), revision: String(revision), source: String(source), unitId: String(unitId), title: `${node.title} · 근거 원문` });
  };
  return <aside className="jm-detail" aria-label="노드 상세" data-testid="jm-detail">
    <div className="jm-tags"><span className={`jm-tag l-${node.layer} mono`}>{node.layer}계층 · {layerName(node.layer)}</span> <span className="jm-tag kind">{KIND_LABEL[node.kind] || node.kind}</span></div>
    <h2>{mapNodeTitleLabel(node.title)}</h2>
    <p className="jm-id"><span>ID</span> <code className="mono" data-testid="jm-short-id" title={node.id}>{node.id.slice(0, 8)}…</code> <button type="button" className="jm-copy" onClick={copy} aria-label="ID 복사">{copied ? '복사됨' : '복사'}</button></p>
    <dl>{rows.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value || '—'}</dd></div>)}</dl>
    {loading && !data && <p role="status">상세를 불러오는 중…</p>}
    {data && <div className="jm-trace">
      <h3 data-testid="jm-up-count">↑ 근거 쪽으로 {data.upstream_count ?? 0}개</h3>
      <div className="jm-chips">{data.upstream.map((n) => <button key={n.id} type="button" className={`l-${n.layer}`} title={mapNodeTitleLabel(n.title)} onClick={() => onPick(n.id)}><small>{KIND_LABEL[n.kind]}</small> {tileTitle(n.kind, n.title)}</button>)}</div>
      <h3 data-testid="jm-down-count">↓ 실행 쪽으로 {data.downstream_count ?? 0}개</h3>
      <div className="jm-chips">{data.downstream.map((n) => <button key={n.id} type="button" className={`l-${n.layer}`} title={mapNodeTitleLabel(n.title)} onClick={() => onPick(n.id)}><small>{KIND_LABEL[n.kind]}</small> {tileTitle(n.kind, n.title)}</button>)}</div>
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
