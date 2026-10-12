// One viewport-sized (@2x) screenshot of a route, with every /api call answered by fixtures.mjs.
// Needs the Vite dev server that shoot.mjs starts (KEEP_VITE=1 node scripts/readme/mock/shoot.mjs main) on 127.0.0.1:5199.
// Usage: node scripts/readme/mock/viewport.mjs <path> <out.png> [scrollY] [review]
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { routeApi } from './fixtures.mjs';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.resolve(process.env.FRONTEND_DIR || path.resolve(HERE, '../../../frontend'), 'package.json'));
const { chromium } = require('@playwright/test');
const [, , route, out, scrollY = '0', prep = ''] = process.argv;
const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
await routeApi(page, { role: 'all', log: () => {} });
await page.goto('http://127.0.0.1:5199' + route, { waitUntil: 'networkidle' });
if (prep === 'review') { await page.locator('nav[aria-label="검토 대기 목록"] > button').first().click(); await page.getByLabel('AI 필요성 수정').waitFor(); }
await page.waitForTimeout(800);
await page.evaluate((y) => window.scrollTo(0, y), Number(scrollY));
await page.waitForTimeout(400);
await page.screenshot({ path: out });
await browser.close();
