import { localizeError } from '../components/statusLabels';

export type ApiError = { status: number; code: string; message: string; details?: unknown; raw?: string };

export function csrfToken(): string | undefined {
  const cookie = document.cookie.split('; ').find((part) => part.startsWith('jev_csrf='));
  if (cookie) return decodeURIComponent(cookie.slice('jev_csrf='.length));
  return document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')?.content || undefined;
}

export const idempotencyKey = () => ({ 'Idempotency-Key': crypto.randomUUID() });

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const method = (init.method || 'GET').toUpperCase();
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const token = csrfToken();
    if (token) headers.set('X-CSRF-Token', token);
  }
  let response: Response;
  try {
    response = await fetch(path, { ...init, method, headers, credentials: 'include' });
  } catch {
    throw { status: 0, code: 'NETWORK_ERROR', message: '서버에 연결할 수 없습니다.' } satisfies ApiError;
  }
  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    throw { status: 401, code: 'UNAUTHORIZED', message: '로그인이 필요합니다.' } satisfies ApiError;
  }
  if (!response.ok) {
    let body: Record<string, unknown> = {};
    try { body = await response.json() as Record<string, unknown>; } catch { /* response may have no JSON body */ }
    const detail = body.detail;
    const normalized = typeof detail === 'object' && detail !== null ? detail as Record<string, unknown> : {};
    throw { status: response.status, code: String(normalized.code || body.code || `HTTP_${response.status}`), message: localizeError(String(normalized.message || (typeof detail === 'string' ? detail : body.message) || response.statusText || '요청을 처리하지 못했습니다.')), raw: String(normalized.message || (typeof detail === 'string' ? detail : body.message) || '') || undefined, details: normalized.details || body.details } satisfies ApiError;
  }
  if (response.status === 204) return undefined as T;
  return await response.json() as T;
}
