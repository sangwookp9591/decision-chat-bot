import { useEffect, useState } from 'react';

export type MascotMedia = 'png' | 'webp' | 'webm';
export type MascotKind = 'wave' | 'idle' | 'hello' | 'thinking' | 'like' | 'surprised';

/** Reduced motion → still PNG; Safari has no WebM alpha → animated WebP; everything else → WebM. */
export function selectMascotMedia(userAgent: string, reducedMotion: boolean): MascotMedia {
  if (reducedMotion) return 'png';
  return /Safari/i.test(userAgent) && !/(Chrome|Chromium|CriOS|Edg)/i.test(userAgent) ? 'webp' : 'webm';
}

export function useMascotMedia(): MascotMedia {
  const [media, setMedia] = useState<MascotMedia>(() => selectMascotMedia(navigator.userAgent, window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches || false));
  useEffect(() => {
    const query = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    const update = () => setMedia(selectMascotMedia(navigator.userAgent, query?.matches || false));
    update(); query?.addEventListener?.('change', update);
    return () => query?.removeEventListener?.('change', update);
  }, []);
  return media;
}

/** Mascot art is decorative (alt=""): the meaning is always carried by the adjacent text. */
export function Mascot({ kind, size = 44, className = '' }: { kind: MascotKind; size?: number; className?: string }) {
  const media = useMascotMedia();
  const animated = kind === 'wave' || kind === 'idle';
  const style = { width: size, height: size };
  if (!animated) return <img className={`mascot ${className}`} data-mascot={kind} src={`/assets/icons/${kind}.webp`} alt="" style={style} />;
  if (media === 'webm') return <video className={`mascot ${className}`} data-mascot={kind} src={`/assets/mascot/${kind}.webm`} poster="/assets/mascot/mascot.png" autoPlay muted loop playsInline aria-hidden="true" style={style} />;
  return <img className={`mascot ${className}`} data-mascot={kind} src={media === 'png' ? '/assets/mascot/mascot.png' : `/assets/mascot/${kind}.webp`} alt="" style={style} />;
}
