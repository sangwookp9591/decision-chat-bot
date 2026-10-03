import { expect, type APIRequestContext, type Browser, type BrowserContext, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

export const tenant = process.env.E2E_TENANT || 't-acc21';
export const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
export const outDir = process.env.ACC_UI_OUT || join(process.cwd(), 'test-results', 'acceptance-ui');
mkdirSync(outDir, { recursive: true });

export type Actor = { ctx: BrowserContext; page: Page; api: APIRequestContext; csrf: () => Promise<string> };

export async function actor(browser: Browser, baseURL: string, role: string, tnt = tenant): Promise<Actor> {
  const ctx = await browser.newContext({ baseURL });
  const res = await ctx.request.post('/api/auth/login', { data: { email: `${role}@${tnt}.dev`, password } });
  expect(res.ok(), `login ${role}@${tnt}: ${res.status()}`).toBeTruthy();
  const page = await ctx.newPage();
  const csrf = async () => (await ctx.storageState()).cookies.find((c) => c.name === 'jev_csrf')?.value || '';
  return { ctx, page, api: ctx.request, csrf };
}

export async function shot(page: Page, name: string) {
  await page.screenshot({ path: join(outDir, `${name}.png`), fullPage: true });
}

export async function submitApi(a: Actor, text: string, files: { name: string; mimeType: string; buffer: Buffer }[] = []) {
  const multipart: Record<string, unknown> = { text };
  if (files.length === 1) multipart.files = files[0];
  const res = await a.api.post('/api/requests', {
    headers: { 'Idempotency-Key': crypto.randomUUID(), 'X-CSRF-Token': await a.csrf() },
    multipart: multipart as never,
  });
  expect(res.status(), await res.text()).toBe(202);
  return (await res.json()).request_id as string;
}

export async function waitJudged(a: Actor, id: string, timeoutMs = 240_000) {
  await expect.poll(async () => {
    const d = await (await a.api.get(`/api/requests/${id}`)).json();
    return ['judgment_pending', 'received'].includes(d.request.status) ? 'pending' : d.request.status;
  }, { timeout: timeoutMs, intervals: [3000] }).not.toBe('pending');
  return (await (await a.api.get(`/api/requests/${id}/judgment`)).json()) as Record<string, any>;
}

export async function pendingReview(rv: Actor, requestId: string) {
  let row: Record<string, any> | undefined;
  await expect.poll(async () => {
    const list = await (await rv.api.get('/api/reviews?status=pending')).json();
    row = list.reviews.find((r: any) => r.request_id === requestId);
    return Boolean(row);
  }, { timeout: 90_000, intervals: [2000] }).toBe(true);
  return row as Record<string, any>;
}

/** Counters that must not move when only reading/replaying (all through the public API). */
export async function visibleTotals(a: Actor) {
  const tasks = (await (await a.api.get('/api/tasks')).json()).tasks.length;
  const reviews = (await (await a.api.get('/api/reviews?status=pending')).json()).reviews.length;
  const list = (await (await a.api.get('/api/requests?limit=100')).json()).items as any[];
  let runs = 0, outputs = 0;
  for (const r of list) {
    const rr = await (await a.api.get(`/api/requests/${r.id}/runs`)).json();
    runs += rr.runs.length;
    for (const run of rr.runs) {
      const j = await a.api.get(`/api/requests/${r.id}/judgment?run_id=${run.id}`);
      if (j.ok()) outputs += ((await j.json()).outputs || []).length;
    }
  }
  return { tasks, reviews, requests: list.length, runs, outputs };
}
