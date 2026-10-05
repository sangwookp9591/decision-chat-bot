import { expect, test } from '@playwright/test';

const taskBase = {
  id: 'task_blocker_e2e', request_id: 'request_blocker_e2e', title: '본업무', method: '일반 기술',
  lead_org: 'IT팀', collab_orgs: [], deliverable: '보고서', predecessors: [], successors: [],
  predecessor_tasks: [{ id: 'confirmation_e2e', title: '선행 확인', confirmation_task: true, status: '완료' }],
  reason: null, block_reasons: ['feasibility_unresolved'], status: '막힘',
};
const tenant = process.env.E2E_TENANT || 't-audit-e2e-1005';
const password = process.env.JEVTRIAGE_DEV_PASSWORD || 'dev-only-change-me';
async function login(page: import('@playwright/test').Page) {
  const response = await page.request.post('/api/auth/login', { data: { email: `team_member@${tenant}.dev`, password } });
  expect(response.ok(), `login failed: ${response.status()}`).toBeTruthy();
}

test('completed confirmation enables the main task from server readiness projection', async ({ page }) => {
  await login(page);
  const task = { ...taskBase, can_start: true, start_blockers: [] };
  await page.route('**/api/tasks**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname !== '/api/tasks' && !url.pathname.startsWith('/api/tasks/')) return route.continue();
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: task.id, status: '진행' }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(url.pathname.endsWith(task.id) ? { task } : { tasks: [task] }) });
  });
  await page.goto('/tasks');
  await page.locator('.task-list button', { hasText: '본업무' }).click();
  const dialog = page.getByRole('dialog', { name: '업무 상세' });
  await expect(dialog).toContainText('선행 확인 · 완료');
  await expect(dialog.getByRole('button', { name: '진행으로 변경' })).toBeEnabled();
  await dialog.getByRole('button', { name: '진행으로 변경' }).click();
  await expect(page.getByRole('status')).toContainText('업무 상태를 갱신했습니다');
});

test('server projected blockers keep start disabled and explain why', async ({ page }) => {
  await login(page);
  const task = { ...taskBase, predecessor_tasks: [{ id: 'confirmation_e2e', title: '선행 확인', confirmation_task: true, status: '진행' }], can_start: false, start_blockers: ['predecessor_incomplete', 'feasibility_unresolved'] };
  await page.route('**/api/tasks**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname !== '/api/tasks' && !url.pathname.startsWith('/api/tasks/')) return route.continue();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(url.pathname.endsWith(task.id) ? { task } : { tasks: [task] }) });
  });
  await page.goto('/tasks');
  await page.locator('.task-list button', { hasText: '본업무' }).click();
  const dialog = page.getByRole('dialog', { name: '업무 상세' });
  await expect(dialog.getByRole('button', { name: '진행으로 변경' })).toBeDisabled();
  await expect(dialog.getByRole('group', { name: '시작 차단 사유' })).toContainText('선행 업무가 아직 완료되지 않았습니다');
  await expect(dialog.getByRole('group', { name: '시작 차단 사유' })).toContainText('개발 가능성');
});
