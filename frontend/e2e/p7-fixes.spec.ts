import { expect, request, test, type Page } from '@playwright/test';

// P7 defects F2–F6 (artifacts/review/browser-retest/VERIFY-P7.md). Live scenarios against a real API + worker (AI_MODE=live).
const tenant = process.env.E2E_TENANT || 't-alpha';
const password = process.env.ILDONGI_DEV_PASSWORD || 'dev-only-change-me';
async function login(page: Page, role: string) {
  const response = await page.request.post('/api/auth/login', { data: { email: `${role}@${tenant}.dev`, password } });
  expect(response.ok(), `login ${role}: ${response.status()}`).toBeTruthy();
}

test('F2 policy: a value typed right after entering the page is the value that gets validated', async ({ browser }) => {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const context = await browser.newContext(); const page = await context.newPage(); // fresh session: no cursor, past policy.published events replay
    await login(page, 'policy_editor');
    const bodies: string[] = [];
    await page.route('**/api/policy/validate', (route) => { bodies.push(route.request().postData() || ''); return route.continue(); });
    await page.goto('/policy');
    await page.getByText('고급: JSON 보기', { exact: true }).click();
    const field = page.getByLabel('선택형 판단 최소 확신도 (JSON)');
    await field.fill('{"ai_need": 1.5}');
    await page.getByRole('button', { name: '서버 검증' }).click();
    await expect(page.getByText('검증 오류', { exact: true })).toBeVisible();
    expect(bodies).toHaveLength(1);
    expect(JSON.parse(bodies[0]).config?.choice_confidence_thresholds ?? JSON.parse(bodies[0]).choice_confidence_thresholds).toEqual({ ai_need: 1.5 });
    await expect(field).toHaveValue(/1\.5/);
    await context.close();
  }
});

test('F3 monitoring: title, filters and finished areas show while the slowest aggregate is still pending', async ({ page }) => {
  await login(page, 'operator');
  await page.route('**/api/monitoring/summary**', async (route) => { await new Promise((resolve) => setTimeout(resolve, 4000)); await route.continue(); });
  await page.goto('/monitoring');
  await expect(page.getByRole('heading', { name: '모니터링' })).toBeVisible({ timeout: 1000 });
  await expect(page.getByRole('group', { name: '시작' })).toBeVisible({ timeout: 1000 });
  await expect(page.getByRole('region', { name: '서비스 수준 목표' }).getByText('접수·조회 가용성')).toBeVisible({ timeout: 3000 });
  await expect(page.getByRole('region', { name: '핵심 지표' })).toHaveAttribute('aria-busy', 'true');
  await expect(page.getByRole('region', { name: '핵심 지표' })).toHaveAttribute('aria-busy', 'false', { timeout: 10_000 });
});

test('F4 list: a request created in another tab appears without reloading a tab that has nothing selected', async ({ browser }) => {
  const context = await browser.newContext(); const a = await context.newPage(); const b = await context.newPage();
  await login(a, 'requester');
  await b.goto('/'); await expect(b.getByRole('heading', { name: '내 요청' })).toBeVisible();
  await b.waitForTimeout(2500); // B is fully loaded and idle
  await a.goto('/');
  await a.getByLabel('요청 내용').fill(`F4 목록 갱신 확인 ${Date.now()}: 회의실 예약 안내 문서를 정리하고 싶습니다.`);
  await a.getByRole('button', { name: '요청 보내기' }).click();
  await expect(a).toHaveURL(/request_id=req_/);
  const id = new URL(a.url()).searchParams.get('request_id')!;
  await expect(b.getByRole('button', { name: new RegExp(id) })).toBeVisible({ timeout: 8000 });
  await context.close();
});

test('F5 result: provisional → final does not move the content (layout-shift after the provisional card)', async ({ page, browserName }) => {
  test.skip(browserName !== 'chromium', 'layout-shift entries exist only in Chromium');
  await login(page, 'requester');
  await page.goto('/');
  await page.evaluate(() => {
    const w = window as unknown as { __shift: number; __armed: boolean };
    w.__shift = 0; w.__armed = false;
    new PerformanceObserver((list) => { for (const entry of list.getEntries() as unknown as Array<{ value: number; hadRecentInput: boolean }>) if (w.__armed && !entry.hadRecentInput) w.__shift += entry.value; }).observe({ type: 'layout-shift', buffered: false });
    new MutationObserver(() => { if (!w.__armed && document.querySelector('.provisional-badge')) w.__armed = true; }).observe(document.body, { childList: true, subtree: true });
  });
  await page.getByLabel('요청 내용').fill('고객 문의 분류에 챗봇을 도입하고 싶습니다. 긴급하지 않고 AI팀이 주관하면 좋겠습니다.');
  await page.getByRole('button', { name: '요청 보내기' }).click();
  await expect(page.locator('.result-summary .summary-text').first()).toHaveText(/\S/, { timeout: 120_000 });
  await expect(page.locator('.provisional-badge')).toHaveCount(0);
  await page.waitForTimeout(500);
  const shift = await page.evaluate(() => (window as unknown as { __shift: number }).__shift);
  console.log('P7_F5_LAYOUT_SHIFT', shift.toFixed(5));
  expect(shift).toBeLessThan(0.005);
});

// UX-7: F5 residue (VERIFY-P8) — layout-shift sums miss movement below the first viewport, so measure document tops of each region while scrolled.
const f5Sentences = [
  { name: 'uncertain', text: '회의실 예약 조회 기능을 만들고 싶습니다.' },
  { name: 'possible', text: '고객 문의 분류에 챗봇을 도입하고 싶습니다. 긴급하지 않고 AI팀이 주관하면 좋겠습니다.' },
];
for (const sentence of f5Sentences) {
  test(`F5 residue (${sentence.name}): summary/judgment/tasks document top and judgment height stay within 4px from provisional to final`, async ({ page }) => {
    test.setTimeout(180_000);
    await page.setViewportSize({ width: 1440, height: 700 });
    await login(page, 'requester');
    await page.goto('/');
    await page.evaluate(() => {
      const w = window as unknown as { __prov: Record<string, number> | null; __final: Record<string, number> | null };
      w.__prov = null; w.__final = null;
      const snap = () => {
        const out: Record<string, number> = {};
        for (const region of ['summary', 'judgment', 'tasks']) { const node = document.querySelector(`[data-region="${region}"]`); if (!node) return null; out[region] = node.getBoundingClientRect().top + window.scrollY; if (region === 'judgment') out.judgmentHeight = node.getBoundingClientRect().height; if (region === 'summary') [...node.children].forEach((child, index) => { out[`summary.${index}`] = child.getBoundingClientRect().height; }); if (region === 'judgment') [...node.querySelector('.judgment-card')!.children].forEach((child, index) => { out[`card0.${index}`] = child.getBoundingClientRect().height; }); }
        return out;
      };
      const tick = () => {
        const provisional = document.querySelector('.provisional-result'); const final = document.querySelector('.result-stack:not(.provisional-result) .summary-text');
        if (provisional) { const now = snap(); if (now) w.__prov = now; } else if (final && w.__prov && !w.__final && (final.textContent || '').trim()) w.__final = snap();
      };
      new MutationObserver(tick).observe(document.body, { childList: true, subtree: true, characterData: true });
      window.addEventListener('scroll', () => undefined);
    });
    await page.getByLabel('요청 내용').fill(sentence.text);
    await page.getByRole('button', { name: '요청 보내기' }).click();
    await page.evaluate(() => window.scrollTo(0, 200)); // scrolled state: regions are measured in document coordinates
    await expect(page.locator('.provisional-result')).toBeVisible({ timeout: 120_000 });
    await expect(page.locator('.result-stack:not(.provisional-result) .summary-text')).toHaveText(/\S/, { timeout: 120_000 });
    await page.waitForTimeout(500);
    const { prov, final, uncertain } = await page.evaluate(() => { const w = window as unknown as { __prov: Record<string, number> | null; __final: Record<string, number> | null }; return { prov: w.__prov, final: w.__final, uncertain: document.querySelectorAll('.uncertain-result').length }; });
    console.log('UX7_F5', sentence.name, JSON.stringify({ prov, final, uncertain }));
    if (process.env.AI_MODE === 'mock') {
      expect(uncertain, `fixture must exercise the ${sentence.name} result layout`).toBe(sentence.name === 'uncertain' ? 1 : 0);
    }
    expect(prov, 'provisional layout captured').not.toBeNull(); expect(final, 'final layout captured').not.toBeNull();
    for (const key of ['summary', 'judgment', 'tasks', 'judgmentHeight']) expect(Math.abs(final![key] - prov![key]), `${key}: ${prov![key]} → ${final![key]}`).toBeLessThanOrEqual(4);
  });
}

test('F6 Korean: evaluation and policy screens show names, not snake_case keys, outside 기술 상세', async ({ page }) => {
  const visibleKeys = async () => page.evaluate(() => {
    const clone = document.querySelector('main, #root')!.cloneNode(true) as HTMLElement;
    clone.querySelectorAll('details, input, textarea, pre, code').forEach((node) => node.remove());
    const keys = ['consensus_required', 'ai_need', 'team_set', 'risk_areas', 'choice_confidence_thresholds', 'noul_probability_thresholds', 'risk_clear_max', 'reviewer_groups', 'evidence_noul_threshold', 'catalog_noul_threshold', 'feature_flags', 'schema_version', 'auto_assign'];
    return keys.filter((key) => (clone.textContent || '').includes(key));
  });
  await login(page, 'policy_editor');
  await page.goto('/policy'); await expect(page.getByRole('group', { name: '선택형 판단 최소 확신도' })).toBeVisible();
  expect(await visibleKeys()).toEqual([]);
  await expect(page.getByText('기술 상세').first()).toBeVisible();
  await login(page, 'labeler');
  await page.goto('/evaluation'); await expect(page.getByRole('heading', { name: '평가 정답 확정' })).toBeVisible();
  await expect(page.getByLabel(/개발 가능성/)).toBeVisible();
  expect(await visibleKeys()).toEqual([]);
});
