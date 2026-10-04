import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { select } from 'd3-selection';
import { zoom as d3zoom, zoomIdentity, type D3ZoomEvent, type ZoomBehavior } from 'd3-zoom';
import type { GraphEdge, GraphLayer } from '../../api/graph';
import { mapNodeTitleLabel } from '../../lib/labels';
import { SCENE, displayEdges, edgePath, KIND_LABEL, layoutScene, tileTitle, type DisplayItem, type Highlight } from './logic';

type Props = {
  expanded?: boolean; items: DisplayItem[]; edges: GraphEdge[]; layers: GraphLayer[]; highlight: Highlight;
  tabStop: string | null; onTabStop: (id: string) => void; onPick: (item: DisplayItem) => void;
  /** Version tabs + one-line summary (top left) and extra controls such as the expand toggle (bottom left). */
  topLeft?: ReactNode; extraControls?: ReactNode;
};
const TILT = 38;

export function MapView({ expanded = false, items, edges, layers, highlight, tabStop, onTabStop, onPick, topLeft, extraControls }: Props) {
  const stage = useRef<HTMLDivElement>(null);
  const behavior = useRef<ZoomBehavior<HTMLDivElement, unknown> | null>(null);
  const pan = useRef<HTMLDivElement>(null);
  const [zoomPercent, setZoomPercent] = useState(100);
  const touched = useRef(false);
  const layout = useMemo(() => layoutScene(items), [items]);
  const links = useMemo(() => displayEdges(items, edges), [items, edges]);
  const layerMeta = new Map(layers.map((layer) => [layer.layer, layer]));
  const sceneHeight = layout.height;

  const fit = useCallback(() => {
    const element = stage.current;
    if (!element || !behavior.current) return;
    const { clientWidth, clientHeight } = element;
    const top = (element.querySelector<HTMLElement>('.jm-top')?.offsetHeight ?? 0) + (element.querySelector('.jm-top') ? 28 : 16);
    const k = Math.max(0.3, Math.min(1.4, clientWidth / (SCENE.width * 1.04), (clientHeight - top - 92) / (sceneHeight * Math.cos(TILT * Math.PI / 180) * 1.2 + 24)));
    const next = zoomIdentity.translate((clientWidth - SCENE.width * k) / 2, top).scale(k);
    select(element).call(behavior.current.transform, next);
  }, [sceneHeight]);

  useEffect(() => {
    const element = stage.current;
    if (!element) return;
    const z = d3zoom<HTMLDivElement, unknown>().scaleExtent([0.25, 3])
      .filter((event: Event) => !(event.target as Element | null)?.closest?.('.jm-overlay') && (event.type === 'wheel' ? (event as WheelEvent).ctrlKey || (event as WheelEvent).metaKey : !(event as MouseEvent).button))
      .on('zoom', (event: D3ZoomEvent<HTMLDivElement, unknown>) => {
        if (event.sourceEvent) touched.current = true;
        if (pan.current) pan.current.style.transform = `translate(${event.transform.x}px,${event.transform.y}px) scale(${event.transform.k})`;
      })
      .on('end', (event: D3ZoomEvent<HTMLDivElement, unknown>) => setZoomPercent(Math.round(event.transform.k * 100)));
    behavior.current = z;
    select(element).call(z);
    return () => { select(element).on('.zoom', null); };
  }, []);
  useLayoutEffect(() => { fit(); }, [fit, items.length, expanded]);
  // The stage resizes with the window (and with the expanded layout): keep the scene fitted only while the user has not zoomed.
  useEffect(() => {
    const element = stage.current;
    if (!element || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => { if (!touched.current) fit(); });
    observer.observe(element);
    return () => observer.disconnect();
  }, [fit]);

  const scaleBy = (factor: number) => { touched.current = true; if (stage.current && behavior.current) select(stage.current).call(behavior.current.scaleBy, factor); };
  const dim = highlight.selected !== null;
  const edgeClass = (entry: { edges: GraphEdge[] }) => entry.edges.some((edge) => highlight.edgeIds.has(edge.id)) ? 'is-path' : dim ? 'is-dim' : '';

  const unskew = { transform: `skewX(${-SCENE.skew}deg)` };
  const skew = `skewX(${SCENE.skew}deg)`;

  return <div className="jm-map">
    <div className="jm-stage" ref={stage} data-testid="jm-stage">
      <div className="jm-pan" ref={pan}>
        <div className="jm-persp" style={{ width: SCENE.width, height: sceneHeight * Math.cos(TILT * Math.PI / 180) + 120 }}>
          <div className="jm-scene" style={{ width: SCENE.width, height: sceneHeight, transform: `rotateX(${TILT}deg)` }}>
            {layout.planes.map((plane) => {
              const meta = layerMeta.get(plane.layer);
              const empty = !items.some((item) => item.layer === plane.layer);
              return <div key={plane.layer} className={`jm-plane l-${plane.layer} ${empty ? 'is-empty' : ''}`} style={{ left: plane.x, top: plane.y, width: plane.w, height: plane.h, transform: skew }} data-layer={plane.layer}>
                {empty && <p className="jm-plane-empty" style={unskew}>이 기준에 해당하는 노드가 없습니다.</p>}
                <div className="jm-plane-head" style={unskew}><strong><span className="jm-plane-num">{meta?.count ?? 0}</span> <span className="jm-plane-name">{meta?.name}</span></strong><span className="jm-plane-desc">{meta?.desc}</span></div>
              </div>;
            })}
            <svg className="jm-lines" width={SCENE.width} height={sceneHeight} aria-hidden="true">
              {links.map((entry) => {
                const a = layout.boxes.get(entry.from), b = layout.boxes.get(entry.to);
                if (!a || !b) return null;
                const counter = entry.edges.some((edge) => edge.props?.role === 'counter');
                return <path key={entry.id} d={edgePath(a, b)} className={`jm-line ${edgeClass(entry)} ${counter ? 'is-counter' : ''}`} data-edge-ids={entry.edges.map((edge) => edge.id).join(' ')} />;
              })}
            </svg>
            {items.map((item) => {
              const box = layout.boxes.get(item.id);
              if (!box) return null;
              const inPath = highlight.nodeIds.has(item.id);
              const state = highlight.selected === item.id ? 'is-selected' : inPath ? 'is-path' : dim ? 'is-dim' : '';
              const full = item.group ? item.label : mapNodeTitleLabel(item.nodes[0].title);
              const kind = KIND_LABEL[item.kind] || item.kind;
              return <button key={item.id} type="button" data-node-id={item.id} data-kind={item.kind} data-layer={item.layer}
                className={`jm-node k-${item.kind} l-${item.layer} ${item.group ? 'is-group' : ''} ${state}`}
                style={{ left: box.x, top: box.y, width: box.w, height: box.h, transform: skew }} title={item.group ? `${kind} ${full} — 눌러서 펼치기` : full}
                tabIndex={tabStop === item.id ? 0 : -1} aria-pressed={item.group ? undefined : highlight.selected === item.id}
                aria-label={item.group ? `${item.layer}계층 ${kind} ${item.label} 묶음. 눌러서 펼치기` : `${item.layer}계층 ${kind} ${full}`}
                onFocus={() => onTabStop(item.id)} onClick={() => onPick(item)}>
                <span className="jm-node-in" style={unskew}><small className="jm-chip">{kind}</small><span className="jm-t">{item.group ? item.label : tileTitle(item.kind, item.nodes[0].title)}</span></span>
                {inPath && <i className="jm-dot" aria-hidden="true" />}
              </button>;
            })}
          </div>
        </div>
      </div>
      <div className="jm-vignette" aria-hidden="true" />
      {topLeft && <div className="jm-overlay jm-top">{topLeft}</div>}
      <div className="jm-overlay jm-zoom" role="group" aria-label="확대·이동">
        <button type="button" aria-label="축소" onClick={() => scaleBy(1 / 1.25)}>−</button>
        <span className="mono" data-testid="jm-zoom-pct" aria-live="polite">{zoomPercent}%</span>
        <button type="button" aria-label="확대" onClick={() => scaleBy(1.25)}>+</button>
        <button type="button" className="jm-fit" onClick={() => { touched.current = false; fit(); }}>전체 보기</button>
        {extraControls}
      </div>
      <div className="jm-overlay jm-legend" aria-hidden="true"><span><i className="rel" />관계</span><span><i className="path" />선택 경로</span><span><i className="counter" />반례</span></div>
      <p className="jm-hint">드래그로 이동 · Ctrl/⌘+휠 또는 버튼으로 확대</p>
    </div>
  </div>;
}
