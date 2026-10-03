import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Shell } from './App';
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
describe('frontend smoke', () => {
  it('routes unauthenticated sessions to login', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 401 })));
    render(<MemoryRouter><Shell /></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('heading', { name: '로그인이 필요합니다' })).toBeTruthy());
  });
});
