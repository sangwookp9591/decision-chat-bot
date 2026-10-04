import { chromium, webkit } from '/Users/psw/Projects/decision-chat-bot/frontend/node_modules/@playwright/test/index.mjs';
const out = process.argv[2], tag = process.argv[3] || 'after';
const BASE = 'http://127.0.0.1:6791';
for (const [name, type] of [['chromium', chromium], ['webkit', webkit]]) {
  const browser = await type.launch();
  for (const [w, h] of [[1440, 1000], [960, 900], [375, 800]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h } });
    const page = await ctx.newPage();
    await page.request.post(`${BASE}/api/auth/login`, { data: { email: 'reviewer@t-ux3.dev', password: 'dev-only-change-me' } });
    await page.goto(`${BASE}/judgment-map?rule_id=R-UX-03&view=map`);
    if (w === 375) await page.getByRole('button', { name: '입체 맵' }).click();
    await page.waitForSelector('.jm-stage');
    await page.waitForTimeout(900);
    const stage = page.locator('.jm-board');
    await page.screenshot({ path: `${out}/${tag}-${name}-${w}-before-select.png`, fullPage: true });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    console.log(name, w, 'page overflow px', overflow);
    const step = page.locator('.jm-node[data-kind="RunStep"]').first();
    await step.click();
    await page.waitForTimeout(900);
    await page.screenshot({ path: `${out}/${tag}-${name}-${w}-selected.png`, fullPage: true });
    await ctx.close();
  }
  await browser.close();
}
