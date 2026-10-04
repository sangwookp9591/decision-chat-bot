import { useLayoutEffect, useState, type DragEvent, type KeyboardEvent, type RefObject } from 'react';
import { ATTACH_LIMITS, type ComposerMode } from './conversation';
import { ArrowUpIcon, PlusIcon, StopIcon } from './icons';

const MAX_LINES = 8;

const COPY: Record<ComposerMode, { send: string; placeholder: string; hint: string }> = {
  new: { send: '요청 보내기', placeholder: '필요한 업무와 해결하려는 문제를 적어 주세요', hint: ATTACH_LIMITS },
  info: { send: '답변 보내기', placeholder: '일동이의 질문에 답해 주세요', hint: '답변은 같은 요청의 새 revision으로 접수돼요' },
  file: { send: '다시 첨부해 보내기', placeholder: '읽지 못한 파일 대신 다시 첨부하거나 설명을 적어 주세요', hint: '다시 첨부하면 같은 요청의 새 revision으로 접수돼요' },
};
const size = (bytes: number) => (bytes >= 1048576 ? `${(bytes / 1048576).toFixed(1)} MiB` : `${Math.max(1, Math.ceil(bytes / 1024))} KiB`);

export function Composer({ mode, text, files, busy, openRequest, textRef, attachRef, onText, onAddFiles, onRemoveFile, onSubmit }: {
  mode: ComposerMode; text: string; files: File[]; busy: boolean; openRequest: boolean;
  textRef: RefObject<HTMLTextAreaElement>; attachRef: RefObject<HTMLInputElement>;
  onText: (value: string) => void; onAddFiles: (files: File[]) => void; onRemoveFile: (index: number) => void; onSubmit: () => void;
}) {
  const [dragging, setDragging] = useState(false);
  // The box grows with the text, up to ~8 lines; beyond that the textarea scrolls inside.
  useLayoutEffect(() => {
    const el = textRef.current; if (!el) return;
    el.style.height = 'auto';
    const style = getComputedStyle(el); const line = parseFloat(style.lineHeight) || 24; const pad = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom) || 0;
    if (el.scrollHeight > 0) el.style.height = `${Math.min(el.scrollHeight, line * MAX_LINES + pad)}px`;
  }, [text, textRef]);
  const copy = COPY[mode]; const ready = !busy && (text.trim().length > 0 || files.length > 0);
  const drop = (event: DragEvent) => { event.preventDefault(); setDragging(false); onAddFiles(Array.from(event.dataTransfer?.files || [])); };
  // Enter sends, Shift+Enter adds a line; Ctrl/⌘+Enter also sends. Never while a Korean IME is composing (that Enter commits the syllable).
  const key = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Enter' || event.shiftKey) return;
    if (event.nativeEvent.isComposing || event.keyCode === 229) return;
    event.preventDefault(); if (ready) onSubmit();
  };
  return <form className={`composer${dragging ? ' dragging' : ''}`} aria-label="일동이에게 요청" onSubmit={(event) => { event.preventDefault(); if (ready) onSubmit(); }}
    onDragOver={(event) => { if (event.dataTransfer?.types?.includes('Files')) { event.preventDefault(); setDragging(true); } }} onDragLeave={(event) => { if (event.currentTarget === event.target) setDragging(false); }} onDrop={drop}>
    {dragging && <p className="drop-hint" role="status">여기에 파일을 놓으면 첨부돼요</p>}
    {files.length > 0 && <ul className="chip-list attach-chips" aria-label="첨부할 파일">{files.map((file, index) => <li key={`${file.name}-${index}`} className="file-chip">{file.name} · {size(file.size)}<button type="button" aria-label={`${file.name} 첨부 제거`} onClick={() => onRemoveFile(index)}>×</button></li>)}</ul>}
    <div className="composer-box">
      <label className="icon-button attach-button" title="파일 첨부"><PlusIcon /><input ref={attachRef} aria-label="파일 첨부" type="file" accept=".pdf,.docx,.md" multiple onChange={(event) => { onAddFiles(Array.from(event.target.files || [])); event.target.value = ''; }} /></label>
      <label className="sr-only" htmlFor="request-text">요청 내용</label>
      <textarea id="request-text" ref={textRef} value={text} rows={1} placeholder={copy.placeholder} onChange={(event) => onText(event.target.value)} onKeyDown={key} aria-describedby="composer-hint" />
      <button className="ui-button primary send-button" type="submit" disabled={!ready} aria-label={busy ? '전송 중' : copy.send} title={copy.send}>{busy ? <StopIcon /> : <ArrowUpIcon />}</button>
    </div>
    <p id="composer-hint" className="composer-hint">{copy.hint} · Enter로 보내기 · Shift + Enter로 줄바꿈{mode === 'new' && openRequest ? ' · 보내면 새 요청으로 접수돼요' : ''}</p>
  </form>;
}
