import { expect, test } from '@playwright/test';

async function installFixture(page: import('@playwright/test').Page) {
  await page.route(/\/api\//, async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (!new URL(route.request().url()).pathname.startsWith('/api/')) return route.continue();
    let body: unknown = {};
    if (path === '/api/auth/me') body = { user_id: 'qa-b-operator', tenant_id: 'qa-b-fixture', roles: ['operator'], mode: 'mock' };
    else if (path === '/api/requests') body = { items: [{ id: 'req_A', status: 'completed' }, { id: 'req_B', status: '취소됨' }] };
    else if (path === '/api/requests/req_A/runs') body = { active_run_id: 'run_A', runs: [{ id: 'run_A', status: 'succeeded' }] };
    else if (path === '/api/requests/req_B/runs') body = { active_run_id: null, runs: [] };
    else if (path.endsWith('/flow')) body = { request_id: 'req_A', run_id: 'run_A', live: false, nodes: [{ id: 'step_A', kind: 'code', name: 'A 요청 입력 정리', status: 'succeeded', duration_ms: 100 }], edges: [] };
    else if (path.endsWith('/playback')) body = { request_id: 'req_A', run_id: 'run_A', live: false, events: [], final_result: 'succeeded', reviews: [] };
    else if (path.includes('/steps/')) body = { id: 'step_A', run_id: 'run_A', kind: 'code', name: 'A 요청 입력 정리', status: 'succeeded', duration_ms: 100, config_version: 1, versions: { schema: 1 }, started_at: '2026-10-05T00:00:00Z', ended_at: '2026-10-05T00:00:00.100Z' };
    await route.fulfill({ json: body });
  });
}

test('selecting a request with no runs clears the previous flow and trace', async ({ page }) => {
  await installFixture(page);
  await page.goto('/observatory?request_id=req_A&run_id=run_A');
  await expect(page.locator('.obs-node')).toHaveCount(1);
  await page.locator('.obs-node').click();
  await expect(page.getByRole('dialog', { name: 'Trace 상세' })).toBeVisible();

  await page.getByRole('combobox', { name: '요청 선택', exact: true }).fill('req_B');
  await page.getByRole('option', { name: /req_B/ }).click();

  await expect(page.getByRole('combobox', { name: '실행 선택', exact: true })).toBeDisabled();
  await expect(page.getByRole('dialog', { name: 'Trace 상세' })).toHaveCount(0);
  await expect(page.locator('.obs-node')).toHaveCount(0);
  await expect(page.getByText('이 요청의 실행 기록이 없습니다')).toBeVisible();
});
