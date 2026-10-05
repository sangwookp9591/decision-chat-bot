# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: acceptance/gates.spec.ts >> G05 auto-assigned requests: stored Assignment/Task/HAS_TASK/ASSIGNED_TO/PRECEDES appear on the 업무 screen
- Location: artifacts/review/completeness/scratch/suite/acceptance/gates.spec.ts:35:5

# Error details

```
Error: login reviewer@t-audit-e2e-1005g: 401

expect(received).toBeTruthy()

Received: false
```

# Test source

```ts
  1  | import { expect, type APIRequestContext, type Browser, type BrowserContext, type Page } from '@playwright/test';
  2  | import { mkdirSync } from 'node:fs';
  3  | import { join } from 'node:path';
  4  | 
  5  | export const tenant = process.env.E2E_TENANT || 't-acc21';
  6  | export const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
  7  | export const outDir = process.env.ACC_UI_OUT || join(process.cwd(), 'test-results', 'acceptance-ui');
  8  | mkdirSync(outDir, { recursive: true });
  9  | 
  10 | export type Actor = { ctx: BrowserContext; page: Page; api: APIRequestContext; csrf: () => Promise<string> };
  11 | 
  12 | export async function actor(browser: Browser, baseURL: string, role: string, tnt = tenant): Promise<Actor> {
  13 |   const ctx = await browser.newContext({ baseURL });
  14 |   const res = await ctx.request.post('/api/auth/login', { data: { email: `${role}@${tnt}.dev`, password } });
> 15 |   expect(res.ok(), `login ${role}@${tnt}: ${res.status()}`).toBeTruthy();
     |                                                             ^ Error: login reviewer@t-audit-e2e-1005g: 401
  16 |   const page = await ctx.newPage();
  17 |   const csrf = async () => (await ctx.storageState()).cookies.find((c) => c.name === 'jev_csrf')?.value || '';
  18 |   return { ctx, page, api: ctx.request, csrf };
  19 | }
  20 | 
  21 | export async function shot(page: Page, name: string) {
  22 |   await page.screenshot({ path: join(outDir, `${name}.png`), fullPage: true });
  23 | }
  24 | 
  25 | export async function submitApi(a: Actor, text: string, files: { name: string; mimeType: string; buffer: Buffer }[] = []) {
  26 |   const multipart: Record<string, unknown> = { text };
  27 |   if (files.length === 1) multipart.files = files[0];
  28 |   const res = await a.api.post('/api/requests', {
  29 |     headers: { 'Idempotency-Key': crypto.randomUUID(), 'X-CSRF-Token': await a.csrf() },
  30 |     multipart: multipart as never,
  31 |   });
  32 |   expect(res.status(), await res.text()).toBe(202);
  33 |   return (await res.json()).request_id as string;
  34 | }
  35 | 
  36 | export async function waitJudged(a: Actor, id: string, timeoutMs = 240_000) {
  37 |   await expect.poll(async () => {
  38 |     const d = await (await a.api.get(`/api/requests/${id}`)).json();
  39 |     return ['judgment_pending', 'received'].includes(d.request.status) ? 'pending' : d.request.status;
  40 |   }, { timeout: timeoutMs, intervals: [3000] }).not.toBe('pending');
  41 |   return (await (await a.api.get(`/api/requests/${id}/judgment`)).json()) as Record<string, any>;
  42 | }
  43 | 
  44 | export async function pendingReview(rv: Actor, requestId: string) {
  45 |   let row: Record<string, any> | undefined;
  46 |   await expect.poll(async () => {
  47 |     const list = await (await rv.api.get('/api/reviews?status=pending')).json();
  48 |     row = list.reviews.find((r: any) => r.request_id === requestId);
  49 |     return Boolean(row);
  50 |   }, { timeout: 90_000, intervals: [2000] }).toBe(true);
  51 |   return row as Record<string, any>;
  52 | }
  53 | 
  54 | /** Counters that must not move when only reading/replaying (all through the public API). */
  55 | export async function visibleTotals(a: Actor) {
  56 |   const tasks = (await (await a.api.get('/api/tasks')).json()).tasks.length;
  57 |   const reviews = (await (await a.api.get('/api/reviews?status=pending')).json()).reviews.length;
  58 |   const list = (await (await a.api.get('/api/requests?limit=100')).json()).items as any[];
  59 |   let runs = 0, outputs = 0;
  60 |   for (const r of list) {
  61 |     const rr = await (await a.api.get(`/api/requests/${r.id}/runs`)).json();
  62 |     runs += rr.runs.length;
  63 |     for (const run of rr.runs) {
  64 |       const j = await a.api.get(`/api/requests/${r.id}/judgment?run_id=${run.id}`);
  65 |       if (j.ok()) outputs += ((await j.json()).outputs || []).length;
  66 |     }
  67 |   }
  68 |   return { tasks, reviews, requests: list.length, runs, outputs };
  69 | }
  70 | 
```