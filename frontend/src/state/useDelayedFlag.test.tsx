import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { DelayedFallback, useDelayedFlag, useSlowNotice } from './useDelayedFlag';

function Probe({ on }: { on: boolean }) { return <span data-testid="p">{String(useDelayedFlag(on, 200))}</span>; }
beforeEach(() => vi.useFakeTimers());
afterEach(() => { cleanup(); vi.useRealTimers(); });

describe('useDelayedFlag (Suspensive <Delay/> equivalent)', () => {
  it('does not flash for loads shorter than the delay', () => {
    const { rerender } = render(<Probe on={true} />);
    expect(screen.getByTestId('p')).toHaveTextContent('false');
    act(() => { vi.advanceTimersByTime(150); });
    rerender(<Probe on={false} />);
    act(() => { vi.advanceTimersByTime(500); });
    expect(screen.getByTestId('p')).toHaveTextContent('false');
  });
  it('turns on after the delay and off immediately when loading ends', () => {
    const { rerender } = render(<Probe on={true} />);
    act(() => { vi.advanceTimersByTime(200); });
    expect(screen.getByTestId('p')).toHaveTextContent('true');
    rerender(<Probe on={false} />);
    expect(screen.getByTestId('p')).toHaveTextContent('false');
  });
});

describe('DelayedFallback', () => {
  it('renders nothing for the first 200ms, then the fallback', () => {
    render(<DelayedFallback><p>스켈레톤</p></DelayedFallback>);
    expect(screen.queryByText('스켈레톤')).toBeNull();
    act(() => { vi.advanceTimersByTime(200); });
    expect(screen.getByText('스켈레톤')).toBeInTheDocument();
  });
});

function Slow() { const [on, setOn] = useState(true); const slow = useSlowNotice(on, 5000); return <><button onClick={() => setOn(false)}>끝</button><span data-testid="s">{String(slow)}</span></>; }
describe('useSlowNotice', () => {
  it('flags after 5 seconds and clears when the work ends', () => {
    render(<Slow />);
    act(() => { vi.advanceTimersByTime(4900); });
    expect(screen.getByTestId('s')).toHaveTextContent('false');
    act(() => { vi.advanceTimersByTime(200); });
    expect(screen.getByTestId('s')).toHaveTextContent('true');
    act(() => { screen.getByText('끝').click(); });
    expect(screen.getByTestId('s')).toHaveTextContent('false');
  });
});
