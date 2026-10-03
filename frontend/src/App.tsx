import { useEffect } from 'react';
import { useSession } from './state/session';
import { registerWebMcpTools, unregisterWebMcpTools } from './webmcp';
import { Login } from './pages/Login';
import { AppShell } from './layout/AppShell';
import { LoadingState } from './components';
export function Shell() { const { user, loading } = useSession(); useEffect(() => { if (user) void registerWebMcpTools(); else unregisterWebMcpTools(); }, [user]); if (loading) return <LoadingState label="세션 확인 중" />; return user ? <AppShell /> : <Login />; }
