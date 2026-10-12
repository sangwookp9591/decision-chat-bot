#!/usr/bin/env node
// Screenshot harness: renders the real frontend (Vite dev server) with every /api/** call answered by fixtures.mjs.
// Usage: node harness/shoot.mjs [name ...]     (no names = all shots)
import { spawn } from 'node:child_process';
import { mkdirSync, openSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { routeApi, FIXTURE_IDS } from './fixtures.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND = process.env.FRONTEND_DIR || path.resolve(HERE, '../../../frontend');
const OUT = path.join(HERE, 'out');
const PORT = Number(process.env.PORT || 5199);
const BASE = `http://127.0.0.1:${PORT}`;
process.env.PLAYWRIGHT_BROWSERS_PATH ||= '/opt/pw-browsers';
const { chromium } = createRequire(path.join(FRONTEND, 'package.json'))('@playwright/test');

const { REQ, RUN } = FIXTURE_IDS;
/** name → { path, role?, prepare?(page) } */
const SHOTS = {
  'main': { path: '/' },
  'main-result': { path: `/?request_id=${REQ.sap}`, ready: '.result-brief' },
  'review': { path: '/review', prepare: async (page) => { await page.locator('nav[aria-label="검토 대기 목록"] > button').first().click(); await page.getByLabel('AI 필요성 수정').waitFor(); } },
  'tasks': { path: '/tasks', ready: '.task-list button' },
  'observatory': { path: `/observatory?request_id=${REQ.sap}&run_id=${RUN.sap2}`, ready: 'ol.obs-flow' },
  'judgment-map': { path: '/judgment-map', ready: '[data-testid="jm-board"]' },
  'monitoring': { path: '/monitoring', ready: '.failure-list' },
  'cases': { path: '/cases', ready: '.cases-detail' },
  'learning': { path: `/learning?candidate_id=${FIXTURE_IDS.learningCandidate}`, ready: '.learning-detail .learning-card' },
  'evaluation': { path: '/evaluation', ready: '.eval-sample' },
  'policy': { path: '/policy', ready: '.policy-table, .policy-version-cards' },
  'login': { path: '/', role: 'anonymous', ready: '.login-card' },
};
const ERROR_TEXT = /불러오지 못했습니다|요청을 처리하지 못했습니다|서버에 연결할 수 없습니다|오류:|권한이 없습니다|찾을 수 없습니다/;

/** Use Playwright's own browser when its revision is installed; otherwise fall back to any preinstalled Chromium (never downloads). */
async function launchChromium() {
  try { return await chromium.launch(); } catch (error) {
    const { readdirSync, existsSync } = await import('node:fs');
    const root = process.env.PLAYWRIGHT_BROWSERS_PATH;
    const candidates = [process.env.CHROMIUM_PATH, ...(root ? readdirSync(root) : []).filter((d) => /^chromium-\d+$/.test(d)).sort().reverse().map((d) => path.join(root, d, 'chrome-linux', 'chrome'))].filter(Boolean);
    const executablePath = candidates.find((p) => existsSync(p));
    if (!executablePath) throw error;
    console.log(`[chromium] bundled revision missing, using ${executablePath}`);
    return chromium.launch({ executablePath });
  }
}
async function serverUp() { try { const r = await fetch(BASE, { signal: AbortSignal.timeout(1500) }); return r.ok; } catch { return false; } }
async function ensureVite() {
  if (await serverUp()) { console.log(`[vite] reusing ${BASE}`); return null; }
  console.log(`[vite] starting on ${BASE}`);
  // Output goes to a file (not a pipe) so a KEEP_VITE=1 server survives this process and is reused next run.
  mkdirSync(OUT, { recursive: true });
  const logFd = openSync(path.join(OUT, 'vite.log'), 'a');
  const child = spawn('npx', ['vite', '--host', '127.0.0.1', '--port', String(PORT), '--strictPort'], { cwd: FRONTEND, stdio: ['ignore', logFd, logFd], detached: true });
  if (process.env.KEEP_VITE) child.unref();
  for (let i = 0; i < 120; i++) { if (await serverUp()) return child; await new Promise((r) => setTimeout(r, 500)); }
  throw new Error('vite did not start within 60s');
}

async function shoot(browser, name, spec) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, locale: 'ko-KR', timezoneId: 'Asia/Seoul', reducedMotion: 'reduce' });
  const page = await context.newPage();
  const problems = [];
  page.on('console', (msg) => { if (msg.type() === 'error' && !(spec.role === 'anonymous' && /401/.test(msg.text()))) problems.push(`console.error: ${msg.text()}`); });
  page.on('pageerror', (err) => problems.push(`pageerror: ${err.message}`));
  const { unknown } = await routeApi(page, { role: spec.role || 'all', log: () => {} });
  await page.goto(BASE + spec.path, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => problems.push('networkidle timeout'));
  if (spec.ready) await page.locator(spec.ready).first().waitFor({ timeout: 10000 }).catch(() => problems.push(`ready selector not found: ${spec.ready}`));
  if (spec.prepare) { try { await spec.prepare(page); await page.waitForLoadState('networkidle', { timeout: 10000 }); } catch (e) { problems.push(`prepare failed: ${e.message.split('\n')[0]}`); } }
  await page.waitForTimeout(800);
  const texts = await page.evaluate((source) => {
    const re = new RegExp(source);
    const hits = new Set();
    document.querySelectorAll('[role="alert"], .error, .ui-error, .empty, .learning-empty, .learning-error, .monitor-field-error, .review-error, .obs-error').forEach((el) => { const t = el.textContent.trim(); if (t) hits.add(`${el.getAttribute('role') === 'alert' ? 'alert' : el.className}: ${t.slice(0, 140)}`); });
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) { const t = walker.currentNode.textContent.trim(); if (re.test(t)) hits.add(`text: ${t.slice(0, 140)}`); }
    return [...hits];
  }, ERROR_TEXT.source);
  const skeletons = await page.locator('.skeleton, .ui-skeleton, .sk, [aria-busy="true"]').count();
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  await context.close();
  const notes = [...problems, ...texts.map((t) => `ui: ${t}`), ...(skeletons ? [`skeleton/busy elements: ${skeletons}`] : []), ...unknown.map((u) => `unmocked: ${u}`)];
  console.log(`\n■ ${name} → ${file}${notes.length ? '' : '  (clean)'}`);
  notes.forEach((n) => console.log(`   - ${n}`));
  return notes;
}

const wanted = process.argv.slice(2);
const bad = wanted.filter((n) => !SHOTS[n]);
if (bad.length) { console.error(`unknown shot(s): ${bad.join(', ')}\navailable: ${Object.keys(SHOTS).join(', ')}`); process.exit(2); }
mkdirSync(OUT, { recursive: true });
const vite = await ensureVite();
const browser = await launchChromium();
let failures = 0;
try {
  for (const name of wanted.length ? wanted : Object.keys(SHOTS)) {
    try { await shoot(browser, name, SHOTS[name]); } catch (e) { failures++; console.log(`\n■ ${name} FAILED: ${e.message}`); }
  }
} finally {
  await browser.close();
  if (vite && !process.env.KEEP_VITE) { try { process.kill(-vite.pid); } catch { vite.kill(); } }
}
process.exit(failures ? 1 : 0);
