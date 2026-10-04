import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { createPrefetcher, PrefetchNavLink, routeLoaders } from './routes';

afterEach(cleanup);
describe('route prefetch', () => {
  it('loads a route chunk once, only for known paths', () => {
    const monitoring = vi.fn().mockResolvedValue({});
    const prefetch = createPrefetcher({ '/monitoring': monitoring });
    prefetch('/monitoring'); prefetch('/monitoring'); prefetch('/nope');
    expect(monitoring).toHaveBeenCalledTimes(1);
  });
  it('a failed prefetch can be retried later', async () => {
    const loader = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue({});
    const prefetch = createPrefetcher({ '/a': loader });
    prefetch('/a'); await Promise.resolve(); await Promise.resolve(); prefetch('/a');
    expect(loader).toHaveBeenCalledTimes(2);
  });
  it('menu hover and keyboard focus prefetch the target route', () => {
    const prefetch = vi.fn();
    render(<MemoryRouter><PrefetchNavLink to="/monitoring" prefetch={prefetch}>모니터링</PrefetchNavLink></MemoryRouter>);
    fireEvent.mouseEnter(screen.getByRole('link', { name: '모니터링' }));
    fireEvent.focus(screen.getByRole('link', { name: '모니터링' }));
    expect(prefetch).toHaveBeenCalledWith('/monitoring');
  });
  it('every sidebar route except the landing page is a separate chunk', () => {
    expect(Object.keys(routeLoaders).sort()).toEqual(['/evaluation', '/judgment-map', '/learning', '/monitoring', '/observatory', '/policy', '/review', '/tasks']);
  });
});
