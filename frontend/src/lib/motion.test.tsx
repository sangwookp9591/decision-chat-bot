import { act, cleanup, render, renderHook, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Button, Tabs } from '../components';
import { CountUp, MOTION, PressScale, armRouteMotion, prefersReducedMotion, staggerStyle, useCountUp, useStaggerIn } from './motion';

function mockReduced(reduced: boolean) {
  vi.stubGlobal('matchMedia', (q: string) => ({ matches: reduced && q.includes('reduce'), media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent: () => false, onchange: null }));
}
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); });

describe('motion utilities', () => {
  it('reads prefers-reduced-motion', () => { mockReduced(true); expect(prefersReducedMotion()).toBe(true); mockReduced(false); expect(prefersReducedMotion()).toBe(false); });
  it('staggerStyle sets --i', () => expect(staggerStyle(3)).toEqual({ '--i': 3 }));
  it('useStaggerIn indexes children and marks the container', () => {
    function List() { const ref = useStaggerIn<HTMLUListElement>(); return <ul ref={ref} data-testid="l"><li>a</li><li>b</li><li>c</li></ul>; }
    render(<List />); const ul = screen.getByTestId('l');
    expect(ul.classList.contains('m-stagger')).toBe(true);
    expect(Array.from(ul.children).map((c) => (c as HTMLElement).style.getPropertyValue('--i'))).toEqual(['0', '1', '2']);
  });
  it('useCountUp returns the target immediately when motion is reduced', () => { mockReduced(true); const { result } = renderHook(() => useCountUp(42)); expect(result.current).toBe(42); });
  it('useCountUp eases toward a new target and lands exactly on it', () => {
    mockReduced(false); vi.useFakeTimers();
    let now = 0; vi.spyOn(performance, 'now').mockImplementation(() => now);
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => setTimeout(() => { now += 16; cb(now); }, 16) as unknown as number);
    vi.stubGlobal('cancelAnimationFrame', (id: number) => clearTimeout(id));
    const { result, rerender } = renderHook(({ n }) => useCountUp(n, 200), { initialProps: { n: 0 } });
    expect(result.current).toBe(0);
    rerender({ n: 100 });
    act(() => { vi.advanceTimersByTime(80); });
    expect(result.current).toBeGreaterThan(0); expect(result.current).toBeLessThan(100);
    act(() => { vi.advanceTimersByTime(400); });
    expect(result.current).toBe(100);
  });
  it('CountUp keeps the final value readable for assistive tech', () => { mockReduced(true); render(<CountUp value={7} />); expect(screen.getByText('7', { selector: '.sr-only' })).toBeInTheDocument(); });
  it('PressScale marks pressable surfaces', () => { render(<PressScale data-testid="p">x</PressScale>); expect(screen.getByTestId('p')).toHaveAttribute('data-press'); });
  it('motion tokens mirror the CSS', () => { expect(MOTION.press).toBe(120); expect(MOTION.base).toBe(240); expect(MOTION.staggerStep).toBe(36); });
});

describe('route entrance gate', () => {
  it('stays off on page load and arms on the first in-app link click', () => {
    delete document.documentElement.dataset.motion; armRouteMotion();
    expect(document.documentElement.dataset.motion).toBeUndefined();
    const a = document.createElement('a'); a.href = '/review'; document.body.append(a);
    a.addEventListener('click', (e) => e.preventDefault()); a.click();
    expect(document.documentElement.dataset.motion).toBe('route'); a.remove();
  });
});

describe('Button (TDS size/variant/color)', () => {
  it('keeps legacy variants', () => { render(<Button variant="secondary">a</Button>); expect(screen.getByRole('button')).toHaveClass('ui-button', 'secondary'); });
  it('maps TDS props to classes', () => {
    render(<Button size="large" tone="weak" color="danger" block>x</Button>);
    expect(screen.getByRole('button')).toHaveClass('size-large', 'c-danger', 't-weak', 'block');
  });
  it('loading disables and flags busy', () => { render(<Button loading>x</Button>); const b = screen.getByRole('button'); expect(b).toBeDisabled(); expect(b).toHaveAttribute('aria-busy', 'true'); });
  it('fill is the default tone (no t-weak)', () => { render(<Button color="dark">x</Button>); expect(screen.getByRole('button')).not.toHaveClass('t-weak'); });
});

describe('Tabs', () => {
  it('keeps tab semantics and selection', () => {
    const onChange = vi.fn(); render(<Tabs tabs={[{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }]} value="b" onChange={onChange} />);
    expect(screen.getByRole('tab', { name: 'B' })).toHaveAttribute('aria-selected', 'true');
    act(() => screen.getByRole('tab', { name: 'A' }).click()); expect(onChange).toHaveBeenCalledWith('a');
  });
});
