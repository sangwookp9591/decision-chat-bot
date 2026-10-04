import { useEffect, useState, type ReactNode } from 'react';

/**
 * `true` only after `active` has stayed true for `delayMs`; drops to `false` at once. Same idea as Toss's
 * Suspensive `<Delay/>` (loading UI is withheld for ~200ms so short loads never flash a skeleton). A 10-line
 * hook instead of a new dependency: we only need the delay, not Suspensive's Suspense/ErrorBoundary kit.
 */
export function useDelayedFlag(active: boolean, delayMs = 200): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    if (!active) { setOn(false); return; }
    const timer = window.setTimeout(() => setOn(true), delayMs);
    return () => window.clearTimeout(timer);
  }, [active, delayMs]);
  return active && on;
}

/** Suspense/loading fallback that stays empty for the first `delayMs`. */
export function DelayedFallback({ children, delayMs = 200 }: { children: ReactNode; delayMs?: number }) {
  return <>{useDelayedFlag(true, delayMs) ? children : null}</>;
}

/** `true` once `active` work has taken longer than `thresholdMs` ("평소보다 오래 걸리고 있어요" notice). */
export function useSlowNotice(active: boolean, thresholdMs = 5000): boolean {
  return useDelayedFlag(active, thresholdMs);
}
