import { useEffect, useState } from 'react';

export type MascotMedia = 'png' | 'webp';
export type MascotKind = 'wave' | 'nod' | 'shy' | 'hello' | 'thinking' | 'like' | 'surprised';

/** Reduced motion → still PNG; otherwise transparent animated WebP (supported by every target browser). */
export function selectMascotMedia(reducedMotion: boolean): MascotMedia {
  return reducedMotion ? 'png' : 'webp';
}

export function useMascotMedia(): MascotMedia {
  const [media, setMedia] = useState<MascotMedia>(() => selectMascotMedia(window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches || false));
  useEffect(() => {
    const query = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    const update = () => setMedia(selectMascotMedia(query?.matches || false));
    update(); query?.addEventListener?.('change', update);
    return () => query?.removeEventListener?.('change', update);
  }, []);
  return media;
}

/** Mascot art is decorative (alt=""): the meaning is always carried by the adjacent text. */
export function Mascot({ kind, size = 44, className = '' }: { kind: MascotKind; size?: number; className?: string }) {
  const media = useMascotMedia();
  const animated = kind === 'wave' || kind === 'nod' || kind === 'shy';
  const style = { width: size, height: size };
  if (!animated) return <img className={`mascot ${className}`} data-mascot={kind} src={`/assets/icons/${kind}.webp`} alt="" style={style} />;
  return <img className={`mascot ${className}`} data-mascot={kind} src={media === 'png' ? '/assets/mascot/mascot.png' : `/assets/mascot/${kind}.webp`} alt="" style={style} />;
}
