import { useEffect, useRef, useState } from 'react';
import { requestApi, type SourceDocument } from '../api/requests';
import { Drawer, LoadingState } from './index';
import { anchorScrollTop, findAnchorIndex, groupUnits, noSourceNotice, unitLabel, type ViewerTarget } from './evidenceViewerLogic';
import './EvidenceViewer.css';

export type { ViewerTarget } from './evidenceViewerLogic';
const KIND_NAME = { pdf: 'PDF', docx: 'DOCX', md: 'MD', chat: '채팅' } as const;

/** Source panel: every extracted unit of one revision source in order, anchored on unit_id (= EvidenceSpan id). */
export function EvidenceViewer({ target, onClose }: { target: ViewerTarget | null; onClose: () => void }) {
  const [doc, setDoc] = useState<SourceDocument | null>(null);
  const [failed, setFailed] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);
  const key = target ? `${target.requestId}|${target.revision}|${target.source}` : '';

  useEffect(() => {
    setDoc(null); setFailed(false);
    if (!target) return;
    let live = true;
    requestApi.document(target.requestId, target.revision, target.source).then((value) => { if (live) setDoc(value); }, () => { if (live) setFailed(true); });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const anchorIndex = doc && target ? findAnchorIndex(doc.units, target.unitId) : -1;
  useEffect(() => {
    const box = scroller.current;
    if (!doc || !target || !box || anchorIndex < 0) return;
    const element = Array.from(box.querySelectorAll<HTMLElement>('[data-unit-id]')).find((el) => el.dataset.unitId === target.unitId);
    if (!element) return;
    box.scrollTo({ top: anchorScrollTop(element.offsetTop - box.offsetTop, element.offsetHeight, box.clientHeight, box.scrollHeight) });
  }, [doc, target, anchorIndex]);

  const title = target?.title || (doc ? `원문 · ${doc.filename || '채팅 입력'}` : '원문');
  return <Drawer open={Boolean(target)} title={title} onClose={onClose}>
    {failed && <p role="alert">원문을 불러오지 못했습니다. 권한이 없거나 문서가 더 이상 없을 수 있습니다.</p>}
    {!doc && !failed && <LoadingState label="원문을 불러오는 중" />}
    {doc && <div className="ev-viewer">
      <p className="ev-meta">{KIND_NAME[doc.kind]} · {doc.filename || '채팅 입력'} · revision {doc.revision} · 단위 {doc.units.length}개</p>
      {noSourceNotice(doc.can_read_source) && <p role="note" className="ev-denied">{noSourceNotice(doc.can_read_source)}</p>}
      {anchorIndex < 0 && <p role="status" className="ev-missing">해당 근거 위치를 문서에서 찾지 못했습니다. 아래는 문서의 전체 단위입니다.</p>}
      <div className="ev-scroll" ref={scroller} tabIndex={0} aria-label="원문 단위 목록" data-testid="ev-scroll">
        {groupUnits(doc.kind, doc.units).map((group) => <section key={group.key} className="ev-group">
          {group.heading && <h3 className="ev-page">{group.heading}</h3>}
          {group.units.map((unit) => {
            const hit = unit.unit_id === target?.unitId;
            return <div key={unit.unit_id} data-unit-id={unit.unit_id} className={`ev-unit ${hit ? 'is-anchor' : ''}`} aria-current={hit ? 'location' : undefined}>
              <span className="ev-label mono">{unitLabel(doc.kind, unit.location)}</span>
              {doc.can_read_source ? <p>{unit.text}</p> : <p className="ev-hidden">원문 비공개</p>}
            </div>;
          })}
        </section>)}
      </div>
    </div>}
  </Drawer>;
}
