import { useEffect, useRef, useState } from 'react';
import './ui.css';

export function selectMascotMedia(userAgent: string, reducedMotion: boolean): 'png' | 'webp' | 'webm' {
  if (reducedMotion) return 'png';
  return /Safari/i.test(userAgent) && !/(Chrome|Chromium|CriOS|Edg)/i.test(userAgent) ? 'webp' : 'webm';
}

export function ChatWidget({ onSend }: { onSend?: (message: string) => void }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [media, setMedia] = useState<'png' | 'webp' | 'webm'>('webm');
  const [result, setResult] = useState<{ urgency?: unknown; review?: boolean; summary?: string } | null>(null);
  const launcherRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const query = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    const update = () => setMedia(selectMascotMedia(navigator.userAgent, query?.matches || false));
    update();
    query?.addEventListener?.('change', update);
    return () => query?.removeEventListener?.('change', update);
  }, []);

  useEffect(() => {
    const receive = (event: Event) => setResult((event as CustomEvent<typeof result>).detail);
    window.addEventListener('chat:result', receive);
    return () => window.removeEventListener('chat:result', receive);
  }, []);

  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    const getFocusable = () => panel?.querySelectorAll<HTMLElement>('button:not([disabled]),textarea:not([disabled]),input:not([disabled]),a[href]');
    getFocusable()?.[0]?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); setOpen(false); return; }
      if (event.key !== 'Tab') return;
      const nodes = Array.from(getFocusable() || []);
      if (!nodes.length) { event.preventDefault(); return; }
      if (event.shiftKey && document.activeElement === nodes[0]) { event.preventDefault(); nodes[nodes.length - 1].focus(); }
      else if (!event.shiftKey && document.activeElement === nodes[nodes.length - 1]) { event.preventDefault(); nodes[0].focus(); }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => { document.removeEventListener('keydown', onKeyDown); launcherRef.current?.focus(); };
  }, [open]);

  const urgent = String(result?.urgency || '').toLowerCase().includes('긴급');
  const icon = urgent ? null : result?.review ? 'surprised' : result ? 'like' : 'hello';
  const asset = `/assets/mascot/idle.${media}`;
  return <>
    <button ref={launcherRef} type="button" className="chat-launcher" aria-label="일동이와 채팅 열기" aria-expanded={open} onClick={() => setOpen(true)}>
      {media === 'webm' ? <video src={asset} autoPlay muted loop playsInline aria-hidden="true" /> : <img src={asset} alt="" aria-hidden="true" />}
      <span>일동이와 채팅</span>
    </button>
    {open && <div role="region" aria-label="일동이 채팅"><section ref={panelRef} className="chat-panel" role="dialog" aria-modal="true" aria-labelledby="chat-title">
      <header><div><img src="/assets/icons/hello.webp" alt="" /><strong id="chat-title">일동이 채팅</strong></div><button className="ui-button plain" aria-label="채팅 닫기" onClick={() => setOpen(false)}>×</button></header>
      <div className="chat-content">{urgent ? <div className="chat-urgent" role="alert">⚠ 긴급 요청은 사람의 확인이 필요합니다.</div> : <img className="chat-mascot" src={`/assets/icons/${icon}.webp`} alt="" />}<h2>{result ? (urgent ? '긴급 확인 필요' : result.review ? '검토가 필요해요' : '요청을 정리했어요') : '무엇을 도와드릴까요?'}</h2><p>{result?.summary || '요청 내용을 입력하면 접수 화면에서 이어서 처리할 수 있어요.'}</p></div>
      <form className="chat-compose" onSubmit={(event) => { event.preventDefault(); if (text.trim()) { onSend?.(text.trim()); setText(''); setOpen(false); } }}><label className="sr-only" htmlFor="chat-message">메시지</label><textarea id="chat-message" value={text} onChange={(event) => setText(event.target.value)} placeholder="요청 내용을 입력하세요" /><button className="ui-button primary" type="submit">보내기</button></form>
    </section></div>}
  </>;
}
