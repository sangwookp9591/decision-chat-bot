import { act, cleanup, render, renderHook, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Button, Tabs } from '../components';
import { CountNumber, CountUp, MOTION, PressScale, armRouteMotion, prefersReducedMotion, staggerStyle, useCountUp, useSlideIndicator, useStaggerIn } from './motion';

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

describe('count-up entrance (screens)', () => {
  const frames = () => {
    let now = 0; vi.spyOn(performance, 'now').mockImplementation(() => now);
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => setTimeout(() => { now += 16; cb(now); }, 16) as unknown as number);
    vi.stubGlobal('cancelAnimationFrame', (id: number) => clearTimeout(id));
  };
  afterEach(() => { delete document.documentElement.dataset.motion; });
  it('CountNumber is one plain text node showing the final value on a fresh page load (no half-counted frames for first paint, screenshots, axe)', () => {
    mockReduced(false); frames(); vi.useFakeTimers(); delete document.documentElement.dataset.motion;
    const { container } = render(<CountNumber value={42} format={(n) => `${Math.round(n)}건`} />);
    expect(container.textContent).toBe('42건'); expect(container.querySelectorAll('span')).toHaveLength(1);
  });
  it('after the first in-app navigation it counts up from 0 and lands on the value', () => {
    mockReduced(false); frames(); vi.useFakeTimers(); document.documentElement.dataset.motion = 'route';
    const { container } = render(<CountNumber value={100} duration={200} />);
    expect(Number(container.textContent)).toBeLessThan(100);
    act(() => { vi.advanceTimersByTime(500); });
    expect(container.textContent).toBe('100');
  });
  it('reduced motion shows the value at once even after navigation', () => {
    mockReduced(true); document.documentElement.dataset.motion = 'route';
    const { container } = render(<CountNumber value={9} />); expect(container.textContent).toBe('9');
  });
});

describe('useSlideIndicator', () => {
  it('publishes the pressed/selected child geometry as CSS variables on the container', () => {
    function Seg({ on }: { on: 'a' | 'b' }) { const ref = useSlideIndicator<HTMLDivElement>([on]); return <div ref={ref} data-testid="seg"><button aria-pressed={on === 'a'}>A</button><button aria-pressed={on === 'b'}>B</button></div>; }
    const proto = HTMLElement.prototype; const w = Object.getOwnPropertyDescriptor(proto, 'offsetWidth'), l = Object.getOwnPropertyDescriptor(proto, 'offsetLeft');
    Object.defineProperty(proto, 'offsetWidth', { configurable: true, get() { return 80; } });
    Object.defineProperty(proto, 'offsetLeft', { configurable: true, get() { return this.textContent === 'B' ? 80 : 0; } });
    try {
      const { rerender } = render(<Seg on="a" />); const seg = screen.getByTestId('seg');
      expect(seg.dataset.slide).toBe('on'); expect(seg.style.getPropertyValue('--ind-x')).toBe('0px'); expect(seg.style.getPropertyValue('--ind-w')).toBe('80px');
      rerender(<Seg on="b" />); expect(seg.style.getPropertyValue('--ind-x')).toBe('80px');
    } finally { if (w) Object.defineProperty(proto, 'offsetWidth', w); if (l) Object.defineProperty(proto, 'offsetLeft', l); }
  });
});
