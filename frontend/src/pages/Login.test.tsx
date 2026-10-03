import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Login } from './Login';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const fill = () => { fireEvent.change(screen.getByLabelText('이메일'), { target: { value: 'requester@t-alpha.dev' } }); fireEvent.change(screen.getByLabelText('암호'), { target: { value: 'pw' } }); };

describe('Login (P3-01)', () => {
  it('has email and password fields and a submit button that posts credentials', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('{"ok":true}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const onLoggedIn = vi.fn();
    render(<Login onLoggedIn={onLoggedIn} />);
    expect(screen.getByRole('button', { name: '로그인' })).toBeDisabled();
    fill(); fireEvent.click(screen.getByRole('button', { name: '로그인' }));
    await waitFor(() => expect(onLoggedIn).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({ method: 'POST', body: JSON.stringify({ email: 'requester@t-alpha.dev', password: 'pw' }) }));
  });
  it('shows a Korean error for wrong credentials and stays on the form', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"detail":"Invalid email or password"}', { status: 401 })));
    const onLoggedIn = vi.fn();
    render(<Login onLoggedIn={onLoggedIn} />);
    fill(); fireEvent.click(screen.getByRole('button', { name: '로그인' }));
    expect((await screen.findByRole('alert')).textContent).toBe('이메일 또는 암호가 올바르지 않습니다.');
    expect(onLoggedIn).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: '로그인' })).toBeEnabled();
  });
  it('explains rate limiting', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"detail":"Login temporarily unavailable"}', { status: 429 })));
    render(<Login />); fill(); fireEvent.click(screen.getByRole('button', { name: '로그인' }));
    expect((await screen.findByRole('alert')).textContent).toContain('잠시 후 다시 시도');
  });
});
