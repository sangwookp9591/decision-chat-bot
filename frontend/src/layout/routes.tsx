import { lazy, useEffect, type ComponentProps } from 'react';
import { NavLink } from 'react-router-dom';

/** Page chunks. `/` (Main) stays in the entry bundle because it is the landing page. */
export const routeLoaders: Record<string, () => Promise<unknown>> = {
  '/review': () => import('../pages/Review'),
  '/tasks': () => import('../pages/Tasks'),
  '/observatory': () => import('../pages/Observatory'),
  '/judgment-map': () => import('../pages/JudgmentMap'),
  '/learning': () => import('../pages/Learning'),
  '/monitoring': () => import('../pages/Monitoring'),
  '/policy': () => import('../pages/Policy'),
  '/evaluation': () => import('../pages/Evaluation'),
};
export const Review = lazy(() => import('../pages/Review').then((m) => ({ default: m.Review })));
export const Tasks = lazy(() => import('../pages/Tasks').then((m) => ({ default: m.Tasks })));
export const Observatory = lazy(() => import('../pages/Observatory').then((m) => ({ default: m.Observatory })));
export const JudgmentMap = lazy(() => import('../pages/JudgmentMap').then((m) => ({ default: m.JudgmentMap })));
export const Learning = lazy(() => import('../pages/Learning').then((m) => ({ default: m.Learning })));
export const Monitoring = lazy(() => import('../pages/Monitoring').then((m) => ({ default: m.Monitoring })));
export const Policy = lazy(() => import('../pages/Policy').then((m) => ({ default: m.Policy })));
export const Evaluation = lazy(() => import('../pages/Evaluation').then((m) => ({ default: m.Evaluation }))); 

/** Loads each route chunk at most once; a failed load (offline) is forgotten so a later hover retries. */
export function createPrefetcher(loaders: Record<string, () => Promise<unknown>>) {
  const started = new Set<string>();
  return (path: string) => {
    const load = loaders[path];
    if (!load || started.has(path)) return;
    started.add(path);
    void load().catch(() => started.delete(path));
  };
}
export const prefetchRoute = createPrefetcher(routeLoaders);

/** After first paint, warm the remaining chunks one by one while the browser is idle. */
export function usePrefetchWhenIdle(paths: string[], prefetch: (path: string) => void = prefetchRoute) {
  useEffect(() => {
    const idle = (window as Window & { requestIdleCallback?: (cb: () => void, options?: { timeout: number }) => number; cancelIdleCallback?: (id: number) => void });
    const timers: number[] = [];
    paths.forEach((path, index) => {
      const run = () => prefetch(path);
      timers.push(idle.requestIdleCallback ? idle.requestIdleCallback(run, { timeout: 4000 + index * 500 }) : window.setTimeout(run, 1500 + index * 300));
    });
    return () => timers.forEach((id) => (idle.cancelIdleCallback ? idle.cancelIdleCallback(id) : window.clearTimeout(id)));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}

export function PrefetchNavLink({ prefetch = prefetchRoute, onMouseEnter, onFocus, ...props }: ComponentProps<typeof NavLink> & { prefetch?: (path: string) => void }) {
  const to = typeof props.to === 'string' ? props.to : props.to.pathname || '';
  return <NavLink {...props} onMouseEnter={(event) => { prefetch(to); onMouseEnter?.(event); }} onFocus={(event) => { prefetch(to); onFocus?.(event); }} />;
}
