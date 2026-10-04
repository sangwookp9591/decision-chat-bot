import { useState } from 'react';
import { csrfToken } from '../api/client';
import { localizeError } from '../components/statusLabels';
import { Button } from '../components';

async function login(email: string, password: string): Promise<string | null> {
  let response: Response;
  try {
    response = await fetch('/api/auth/login', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', ...(csrfToken() ? { 'X-CSRF-Token': csrfToken()! } : {}) }, body: JSON.stringify({ email: email.trim(), password }) });
  } catch { return '서버에 연결할 수 없습니다. 네트워크를 확인해 주세요.'; }
  if (response.ok) return null;
  let detail = '';
  try { const body = await response.json() as { detail?: unknown }; detail = typeof body.detail === 'string' ? body.detail : ''; } catch { /* body may be empty */ }
  if (response.status === 401) return localizeError(detail || 'Invalid email or password');
  if (response.status === 429) return localizeError(detail || 'Login temporarily unavailable');
  return localizeError(detail) || '로그인하지 못했습니다. 잠시 후 다시 시도해 주세요.';
}

/** The URL is never changed, so the session refresh after a successful login re-renders the originally requested path. */
export function Login({ onLoggedIn }: { onLoggedIn?: () => void | Promise<void> }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError('');
    const problem = await login(email, password);
    if (problem) { setError(problem); setBusy(false); return; }
    setPassword('');
    try { await onLoggedIn?.(); } finally { setBusy(false); }
  }
  return <main className="login-page"><section className="login-card"><h1>로그인이 필요합니다</h1><p>요청과 판단 결과를 확인하려면 계정으로 로그인해 주세요.</p>
    <form className="login-form" onSubmit={submit} noValidate>
      <label htmlFor="login-email">이메일</label>
      <input id="login-email" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required aria-invalid={Boolean(error)} />
      <label htmlFor="login-password">암호</label>
      <input id="login-password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required aria-invalid={Boolean(error)} />
      {error && <p className="login-error" role="alert">{error}</p>}
      <Button type="submit" disabled={busy || !email.trim() || !password}>{busy ? '로그인 중…' : '로그인'}</Button>
    </form></section></main>;
}
