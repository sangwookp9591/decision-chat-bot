import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppShell } from './AppShell';
import { reviewApi } from '../api/reviews';
import { apiFetch } from '../api/client';

const session = vi.hoisted(() => ({ user: { id: 'u1', name: '김검토', roles: ['reviewer'], mode: 'live' as 'live' | 'mock' | undefined } }));
vi.mock('../state/session', () => ({ useSession: () => ({ user: session.user, loading: false, error: null, refresh: vi.fn() }) }));
vi.mock('../api/reviews', () => ({ reviewApi: { list: vi.fn() } }));
vi.mock('../api/client', () => ({ apiFetch: vi.fn() }));
vi.mock('../pages/Main', () => ({ Main: () => <section><h1>요청 접수</h1></section> }));
vi.mock('./routes', async (original) => ({ ...(await original<typeof import('./routes')>()), usePrefetchWhenIdle: vi.fn() }));

const renderShell = (path = '/') => render(<MemoryRouter initialEntries={[path]}><AppShell /></MemoryRouter>);

beforeEach(() => {
  session.user = { id: 'u1', name: '김검토', roles: ['reviewer'], mode: 'live' };
  vi.mocked(reviewApi.list).mockResolvedValue({ reviews: [{ id: 'r1' }, { id: 'r2' }, { id: 'r3' }] } as never);
  vi.mocked(apiFetch).mockResolvedValue({} as never);
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe('AppShell', () => {
  it('groups the ten menu items into 업무 · 관찰 · 개선', () => {
    renderShell();
    const nav = screen.getByRole('navigation', { name: '주 메뉴' });
    const groups = within(nav).getAllByRole('group');
    expect(groups.map((group) => group.getAttribute('aria-label'))).toEqual(['업무', '관찰', '개선']);
    expect(within(groups[0]).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/', '/review', '/tasks']);
    expect(within(groups[1]).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/observatory', '/judgment-map', '/monitoring']);
    expect(within(groups[2]).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/cases', '/learning', '/evaluation', '/policy']);
  });

  it('shows the user and logout once, inside the account menu', async () => {
    renderShell();
    expect(screen.queryByRole('button', { name: '로그아웃' })).toBeNull();
    const trigger = screen.getByRole('button', { name: /김검토/ });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getAllByText('김검토')).toHaveLength(1);
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    const logout = screen.getByRole('menuitem', { name: '로그아웃' });
    const unauthorized = vi.fn();
    window.addEventListener('auth:unauthorized', unauthorized);
    fireEvent.click(logout);
    await waitFor(() => expect(unauthorized).toHaveBeenCalledTimes(1));
    window.removeEventListener('auth:unauthorized', unauthorized);
    expect(apiFetch).toHaveBeenCalledWith('/api/auth/logout', { method: 'POST' });
  });

  it('closes the account menu with Escape and returns focus to the trigger', () => {
    renderShell();
    const trigger = screen.getByRole('button', { name: /김검토/ });
    fireEvent.click(trigger);
    fireEvent.keyDown(screen.getByRole('menu'), { key: 'Escape' });
    expect(screen.queryByRole('menu')).toBeNull();
    expect(trigger).toHaveFocus();
  });

  it('shows the connection mode badge exactly once', () => {
    const { container } = renderShell();
    expect(container.querySelectorAll('.environment-badge')).toHaveLength(1);
    expect(container.querySelector('.topbar .environment-badge.mode-live')).toHaveTextContent('실서비스');
  });

  it('shows the pending review count for reviewers next to 검토 대기', async () => {
    renderShell();
    const link = screen.getByRole('link', { name: /검토 대기/ });
    await waitFor(() => expect(within(link).getByText('3')).toBeInTheDocument());
    expect(link).toHaveAccessibleName('검토 대기 3건');
    expect(reviewApi.list).toHaveBeenCalledWith('pending');
  });

  it('does not ask for the review queue when the user is not a reviewer', () => {
    session.user = { id: 'u2', name: '이요청', roles: ['requester'], mode: undefined };
    const { container } = renderShell();
    expect(reviewApi.list).not.toHaveBeenCalled();
    expect(container.querySelectorAll('.environment-badge')).toHaveLength(0);
  });

  it('hides the count when no review is pending', async () => {
    vi.mocked(reviewApi.list).mockResolvedValue({ reviews: [] } as never);
    const { container } = renderShell();
    await waitFor(() => expect(reviewApi.list).toHaveBeenCalled());
    expect(container.querySelector('.nav-count')).toBeNull();
    expect(screen.getByRole('link', { name: '검토 대기' })).toBeInTheDocument();
  });

  it('caps a large review count at 99+', async () => {
    vi.mocked(reviewApi.list).mockResolvedValue({ reviews: Array.from({ length: 100 }, (_, i) => ({ id: `r${i}` })) } as never);
    renderShell();
    const link = await screen.findByRole('link', { name: '검토 대기 99건 이상' });
    expect(within(link).getByText('99+')).toBeInTheDocument();
  });

  it('falls back to the user id and shows no role chip when name and roles are empty', () => {
    session.user = { id: 'u3', name: '', roles: [], mode: 'mock' };
    const { container } = renderShell();
    expect(screen.getByRole('button', { name: /u3/ })).toBeInTheDocument();
    expect(container.querySelector('.account-role')).toBeNull();
    expect(container.querySelector('.topbar .environment-badge.mode-mock')).toHaveTextContent(/mock/i);
  });

  it('keeps the menu usable when the review count request fails', async () => {
    vi.mocked(reviewApi.list).mockRejectedValue(new Error('down'));
    renderShell();
    await waitFor(() => expect(reviewApi.list).toHaveBeenCalled());
    expect(screen.getByRole('link', { name: '검토 대기' })).toBeInTheDocument();
  });
});
