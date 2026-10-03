import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../api/client';
import { setEventCursorScope } from './events';
export type SessionUser = { id: string; name: string; roles: string[]; mode?: 'live' | 'mock'; tenantId?: string };
type SessionResponse = { id?: string; name?: string; display_name?: string | null; user_id?: string; tenant_id?: string; roles?: string[]; mode?: 'live' | 'mock' };
type SessionState = { user: SessionUser | null; loading: boolean; error: string | null };
export function useSession() {
  const [state, setState] = useState<SessionState>({ user: null, loading: true, error: null });
  const refresh = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const response = await apiFetch<SessionResponse>('/api/auth/me');
      const id = response.id || response.user_id || '';
      setEventCursorScope(`${response.tenant_id || ''}:${id}`);
      const user: SessionUser = { id, name: response.name || response.display_name || id, roles: response.roles || [], mode: response.mode, tenantId: response.tenant_id };
      setState({ user, loading: false, error: null });
    } catch { setState({ user: null, loading: false, error: null }); }
  }, []);
  useEffect(() => { void refresh(); const unauthorized = () => setState({ user: null, loading: false, error: null }); window.addEventListener('auth:unauthorized', unauthorized); return () => window.removeEventListener('auth:unauthorized', unauthorized); }, [refresh]);
  return { ...state, refresh };
}
