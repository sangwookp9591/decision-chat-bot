import { createElement, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { CSSProperties, DependencyList, HTMLAttributes, ReactNode, RefObject } from 'react';

/** Mirrors the CSS motion tokens in styles/tokens.css (ms). Keep both in sync. */
export const MOTION = { press: 120, fast: 160, base: 240, slow: 320, staggerStep: 36, staggerCap: 10, easeSpring: 'cubic-bezier(0.2, 0.8, 0.2, 1)' } as const;

const QUERY = '(prefers-reduced-motion: reduce)';
const canMatch = () => typeof window !== 'undefined' && typeof window.matchMedia === 'function';

export function prefersReducedMotion(): boolean { return canMatch() && window.matchMedia(QUERY).matches; }

/**
 * Turns on the route-entrance animation after the first in-app navigation (link click or history change).
 * Idempotent; call once at startup (components/index.tsx does). Sets `<html data-motion="route">`.
 */
export function armRouteMotion(): void {
  if (typeof document === 'undefined' || armed) return;
  armed = true;
  const arm = () => { document.documentElement.dataset.motion = 'route'; };
  document.addEventListener('click', (event) => { if ((event.target as Element | null)?.closest?.('a[href]')) arm(); }, true);
  window.addEventListener('popstate', arm);
}
let armed = false;

/** Live `prefers-reduced-motion` value. */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(prefersReducedMotion);
  useEffect(() => {
    if (!canMatch()) return;
    const mq = window.matchMedia(QUERY); const on = () => setReduced(mq.matches);
    on(); mq.addEventListener?.('change', on); return () => mq.removeEventListener?.('change', on);
  }, []);
  return reduced;
}

/** Inline style for one item of a staggered list (use with className="m-stagger" on the parent). */
export function staggerStyle(index: number): CSSProperties { return { '--i': index } as CSSProperties; }

/**
 * Staggered entrance for a list: attach the returned ref to the list container.
 * Children get `--i` (36ms steps, capped at 10 steps) and the container gets `m-stagger`.
 * Re-run on `deps` (e.g. the rows array) to animate newly rendered children.
 */
export function useStaggerIn<T extends HTMLElement = HTMLElement>(deps: DependencyList = []): RefObject<T> {
  const ref = useRef<T>(null);
  useLayoutEffect(() => {
    const el = ref.current; if (!el) return;
    Array.from(el.children).forEach((child, i) => (child as HTMLElement).style.setProperty('--i', String(i)));
    el.classList.add('m-stagger');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return ref;
}

/** Eased count-up toward `target` (ease-out cubic). Returns the target immediately when motion is reduced or rAF is missing. */
export function useCountUp(target: number, duration: number = 600): number {
  const reduced = useReducedMotion();
  const [value, setValue] = useState(target);
  const from = useRef(target);
  useEffect(() => {
    if (reduced || typeof requestAnimationFrame !== 'function' || from.current === target) { from.current = target; setValue(target); return; }
    const start = performance.now(); const origin = from.current; let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration); const eased = 1 - Math.pow(1 - t, 3);
      const next = origin + (target - origin) * eased; from.current = next; setValue(next);
      if (t < 1) raf = requestAnimationFrame(tick); else { from.current = target; setValue(target); }
    };
    raf = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf);
  }, [target, duration, reduced]);
  return value;
}

/** Number that counts up to `value`; assistive tech always reads the final value. */
export function CountUp({ value, duration, format = (n) => String(Math.round(n)) }: { value: number; duration?: number; format?: (n: number) => string }) {
  const shown = useCountUp(value, duration);
  return createElement('span', null, createElement('span', { 'aria-hidden': 'true' }, format(shown)), createElement('span', { className: 'sr-only' }, format(value)));
}

/** Pressable wrapper: scales to 0.97 on pointer-down (CSS `[data-press]`). `card` uses the softer 0.98 card press. */
export function PressScale({ children, card, className = '', ...rest }: HTMLAttributes<HTMLDivElement> & { children?: ReactNode; card?: boolean }) {
  return createElement('div', { ...rest, 'data-press': card ? undefined : '', className: `${card ? 'm-press-card' : ''} ${className}`.trim() }, children);
}
