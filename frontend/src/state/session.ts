import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../api/client';
export type SessionUser = { id: string; name: string; roles: string[]; mode?: 'live' | 'mock' };
type SessionResponse = { id?: string; name?: string; user_id?: string; roles?: string[]; mode?: 'live' | 'mock' };
type SessionState = { user: SessionUser | null; loading: boolean; error: string | null };
export function useSession() {
  const [state, setState] = useState<SessionState>({ user: null, loading: true, error: null });
  const refresh = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try { const response = await apiFetch<SessionResponse>('/api/auth/me'); const id = response.id || response.user_id || ''; const user: SessionUser = { id, name: response.name || id, roles: response.roles || [], mode: response.mode }; setState({ user, loading: false, error: null }); }
    catch { setState({ user: null, loading: false, error: null }); }
  }, []);
  useEffect(() => { void refresh(); const unauthorized = () => setState({ user: null, loading: false, error: null }); window.addEventListener('auth:unauthorized', unauthorized); return () => window.removeEventListener('auth:unauthorized', unauthorized); }, [refresh]);
  return { ...state, refresh };
}
