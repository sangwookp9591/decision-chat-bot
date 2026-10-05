import { expect, test } from '@playwright/test';
import { actor, submitApi, waitJudged } from './acceptance/helpers';

test('Escape closes only the evidence drawer and restores the judgment detail', async ({ browser, baseURL }) => {
  test.setTimeout(120_000);
  const a = await actor(browser, baseURL!, 'requester');
  try {
    const id = await submitApi(a, '회의실 예약 조회 화면을 만듭니다.');
    await waitJudged(a, id);
    await a.page.goto(`/?request_id=${id}`);
    await a.page.getByRole('button', { name: '자세히 보기' }).last().click();
    const detail = a.page.getByRole('dialog', { name: '판단 상세' });
    const evidence = detail.getByRole('button', { name: /근거 열기/ }).first();
    await evidence.focus();
    await evidence.press('Enter');
    const viewer = a.page.getByRole('dialog').filter({ has: a.page.getByTestId('ev-scroll') });
    await expect(viewer).toBeVisible();
    await a.page.keyboard.press('Escape');
    await expect(viewer).toHaveCount(0);
    await expect(detail).toBeVisible();
    await expect(evidence).toBeFocused();
  } finally { await a.ctx.close(); }
});
