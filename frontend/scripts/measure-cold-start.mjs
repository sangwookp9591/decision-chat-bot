// Cold dev-server start measurement: `node scripts/measure-cold-start.mjs [runs=3] [route=/monitoring]`.
// REAL_API=1 (with E2E_API=http://127.0.0.1:<port>) logs in against a real backend instead of mocking /api.
// Each run starts a fresh Vite dev server (empty cacheDir, port E2E_PORT||5481) with a mocked /api, opens the
// route in a fresh browser and reports ms until the route heading is visible. Never touches ports 8191/5391.
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { chromium } from '@playwright/test';

const runs = Number(process.argv[2] || 3); const route = process.argv[3] || '/monitoring';
const port = Number(process.env.E2E_PORT || 5481); const heading = route === '/monitoring' ? '모니터링' : '요청 접수와 판단 결과';
const json = (body) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
const mock = (url) => url.pathname === '/api/auth/me' ? { id: 'u1', name: '운영자', roles: ['operator', 'requester'], tenant_id: 't', mode: 'mock' }
  : url.pathname === '/api/requests' ? { items: [] } : {};

async function once() {
  const cache = mkdtempSync(join(tmpdir(), 'vite-cold-'));
  const server = spawn('npx', ['vite', '--config', 'vite.e2e.config.ts', '--host', '127.0.0.1'], { env: { ...process.env, E2E_PORT: String(port), VITE_CACHE_DIR: cache }, stdio: 'ignore' });
  try {
    const started = Date.now();
    while (Date.now() - started < 30000) { try { if ((await fetch(`http://127.0.0.1:${port}/`)).ok) break; } catch { /* not up yet */ } await new Promise((r) => setTimeout(r, 50)); }
    const browser = await chromium.launch(); const page = await browser.newPage();
    if (!process.env.REAL_API) await page.route((u) => u.pathname.startsWith('/api/'), (r) => { const url = new URL(r.request().url()); r.fulfill(url.pathname.startsWith('/api/monitoring') ? { status: 403, contentType: 'application/json', body: '{"detail":"forbidden"}' } : json(mock(url))); });
    if (process.env.REAL_API) { const login = await page.request.post(`http://127.0.0.1:${port}/api/auth/login`, { data: { email: 'operator@t-alpha.dev', password: process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me' } }); if (!login.ok()) throw new Error(`login ${login.status()}`); }
    page.on('console', (m) => process.env.DEBUG_MEASURE && console.error('console:', m.text())); page.on('pageerror', (e) => console.error('pageerror:', e.message)); const t0 = Date.now();
    await page.goto(`http://127.0.0.1:${port}${route}`);
    try { await page.getByRole('heading', { name: heading }).first().waitFor({ timeout: 15000 }); } catch (error) { console.error(await page.locator('body').innerText()); throw error; }
    const ms = Date.now() - t0; await browser.close(); return ms;
  } finally { server.kill('SIGTERM'); await new Promise((r) => setTimeout(r, 500)); rmSync(cache, { recursive: true, force: true }); }
}
const results = []; for (let i = 0; i < runs; i += 1) results.push(await once());
console.log(JSON.stringify({ route, coldMs: results }));
