import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { Mascot, selectMascotMedia } from './components/Mascot';
import { Modal, StatusBadge } from './components';
import { apiFetch } from './api/client';
import '@testing-library/jest-dom/vitest';
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
describe('shared UI foundations', () => {
  it('shows the accessible status name', () => { render(<StatusBadge status="review" />); expect(screen.getByText('검토 대기')).toBeInTheDocument(); });
  it('traps modal focus and closes on Escape', () => { const onClose = vi.fn(); render(<><button>바깥 버튼</button><Modal open title="상세" onClose={onClose}><button>첫 동작</button><button>마지막 동작</button></Modal></>); const last = screen.getByText('마지막 동작'); expect(screen.getByLabelText('닫기')).toHaveFocus(); last.focus(); fireEvent.keyDown(document, { key: 'Tab' }); expect(screen.getByLabelText('닫기')).toHaveFocus(); fireEvent.keyDown(document, { key: 'Escape' }); expect(onClose).toHaveBeenCalledOnce(); });
  it('uses a still image for reduced motion and WebP only for Safari', () => { expect(selectMascotMedia('Mozilla/5.0 Safari/605.1.15', true)).toBe('png'); expect(selectMascotMedia('Mozilla/5.0 Safari/605.1.15', false)).toBe('webp'); expect(selectMascotMedia('Mozilla/5.0 Chrome/130 Safari/537', false)).toBe('webm'); });
  it('attaches the CSRF cookie to state-changing requests and includes credentials', async () => { Object.defineProperty(document, 'cookie', { configurable: true, value: 'jev_csrf=secret-token' }); const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } })); await apiFetch('/api/example', { method: 'POST', body: JSON.stringify({}) }); const [, init] = fetchSpy.mock.calls[0]; expect((init as RequestInit).credentials).toBe('include'); expect(new Headers((init as RequestInit).headers).get('X-CSRF-Token')).toBe('secret-token'); });
  it('renders the mascot as a still image under reduced motion and a decorative video otherwise', () => {
    const matchMedia = (matches: boolean) => vi.fn().mockReturnValue({ matches, addEventListener: vi.fn(), removeEventListener: vi.fn() });
    window.matchMedia = matchMedia(true) as never; const still = render(<Mascot kind="wave" />);
    expect(still.container.querySelector('img')).toHaveAttribute('src', '/assets/mascot/mascot.png'); expect(still.container.querySelector('video')).toBeNull(); still.unmount();
    window.matchMedia = matchMedia(false) as never; const moving = render(<Mascot kind="wave" />);
    expect(moving.container.querySelector('video')).toHaveAttribute('aria-hidden', 'true');
  });
});
