import { expect, test, type Page } from '@playwright/test';
import { appendFileSync, mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { actor, submitApi, waitJudged, pendingReview } from './acceptance/helpers';

// CHAT-1: request intake is a conversation with 일동이 (no floating widget). Live scenarios (API + worker, JEV_MODE=live, non-sensitive text).
const baseURL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';
const shotDir = resolve(process.cwd(), process.env.CHAT_SHOT_DIR || '../artifacts/review/chat-intake');
mkdirSync(shotDir, { recursive: true });
const shot = (page: Page, name: string) => page.screenshot({ path: join(shotDir, `${test.info().project.name}-${name}.png`), fullPage: true });
const resultIcon = (page: Page) => page.locator('[aria-label="일동이의 답변"]').locator('[data-mascot="like"], [data-mascot="surprised"], .avatar-warning');

test('send → stop → cancelled state → reanalyze the same request', async ({ browser }) => {
  test.setTimeout(300_000);
  const a = await actor(browser, baseURL, 'requester'); const page = a.page;
  await page.goto('/');
  await page.getByLabel('요청 내용').fill('회의실 사용 현황을 월별로 요약하고 중복 예약을 검토해 주세요.');
  await page.getByRole('button', { name: '요청 보내기' }).click();
  await expect(page.getByRole('button', { name: '분석 정지' })).toBeEnabled({ timeout: 30_000 });
  const requestId = new URL(page.url()).searchParams.get('request_id')!;
  await page.getByRole('button', { name: '분석 정지' }).click();
  await expect(page.locator('.cancelled-notice')).toContainText('취소됨', { timeout: 30_000 });
  await shot(page, 'cancelled');
  const before = await (await a.api.get(`/api/requests/${requestId}/runs`)).json();
  expect(before.runs.find((run: { id: string }) => run.id === before.active_run_id).status).toBe('cancelled');
  page.once('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: '다시 분석' }).click();
  await expect(page.locator('.cancelled-notice')).toHaveCount(0, { timeout: 30_000 });
  await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeVisible({ timeout: 240_000 });
  await shot(page, 'reanalyzed');
  const after = await (await a.api.get(`/api/requests/${requestId}/runs`)).json();
  expect(after.runs.length).toBeGreaterThan(before.runs.length);
  expect(after.active_run_id).not.toBe(before.active_run_id);
  const savedJudgment = await (await a.api.get(`/api/requests/${requestId}/judgment`)).json();
  expect(savedJudgment.mode).toBe('live');
  await a.ctx.close();
});

test('send → right bubble → analysis steps → result with icon → reload restores → new request', async ({ browser }) => {
  test.setTimeout(240_000);
  const a = await actor(browser, baseURL, 'requester'); const page = a.page;
  await page.goto('/');
  await expect(page.getByRole('heading', { name: '안녕하세요, 일동이예요' })).toBeVisible();
  await expect(page.getByRole('group', { name: '예시 요청' }).getByRole('button')).toHaveCount(3);
  await shot(page, 'first-screen');
  const text = '사내 회의실 예약 현황을 한곳에서 조회할 수 있는 화면이 필요합니다.';
  await page.getByLabel('요청 내용').fill(text);
  await page.getByRole('button', { name: '요청 보내기' }).click();
  await expect(page.getByRole('group', { name: '내가 보낸 요청' })).toContainText(text, { timeout: 2000 }); // optimistic
  await expect(page.getByRole('heading', { name: '분석 진행' })).toBeVisible();
  for (const step of ['내용 정리', 'Jev 판단', '근거 연결', '업무 나누기', '결과 저장']) await expect(page.locator('.stage-list')).toContainText(step);
  await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeVisible({ timeout: 200_000 });
  await expect(resultIcon(page)).toHaveCount(1); // like / surprised, or the warning without a mascot for urgent
  await expect(page.getByRole('button', { name: '다시 분석', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: /근거 열기|근거 패널 열기/ }).first().click();
  await expect(page.getByRole('heading', { name: '근거 원문' })).toBeVisible();
  await page.keyboard.press('Escape');
  await shot(page, 'result');
  const id = new URL(page.url()).searchParams.get('request_id')!;
  await page.reload();
  await expect(page.getByRole('group', { name: '내가 보낸 요청' })).toContainText(text);
  await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeVisible({ timeout: 30_000 });
  await expect(page.locator(`.request-list .request-row code[title="${id}"]`)).toBeVisible(); // short id in the row, full id on hover
  await expect(page.locator('.request-list .request-row', { hasText: text })).toBeVisible(); // titled by the request's first sentence, not the raw id
  await page.locator('.request-list').getByRole('button', { name: '새 요청' }).click(); // the sidebar's button
  await expect(page).not.toHaveURL(/request_id/);
  await expect(page.getByRole('heading', { name: '안녕하세요, 일동이예요' })).toBeVisible();
  await a.ctx.close();
});

test('unreadable file: 일동이 asks, [다시 첨부] then a corrected file continues as a new revision', async ({ browser }) => {
  test.setTimeout(240_000);
  const a = await actor(browser, baseURL, 'requester'); const page = a.page;
  await page.goto('/');
  await page.getByLabel('요청 내용').fill('분기별 시설 점검 일정을 검색하고 담당자별로 확인하고 싶습니다.');
  await page.getByLabel('파일 첨부').setInputFiles({ name: 'damaged.pdf', mimeType: 'application/pdf', buffer: Buffer.from('not a valid pdf') });
  await expect(page.getByRole('list', { name: '첨부할 파일' })).toContainText('damaged.pdf');
  await page.getByRole('button', { name: '요청 보내기' }).click();
  const ask = page.getByRole('group', { name: '읽기 실패 파일' });
  await expect(ask).toContainText('이 파일을 읽지 못했어요', { timeout: 30_000 });
  await expect(ask).toContainText('damaged.pdf');
  await expect(page.getByRole('button', { name: '요청 보내기' })).toHaveCount(0); // the composer now reads as the re-attach step
  await shot(page, 'file-failure');
  await ask.getByRole('button', { name: '다시 첨부' }).focus();
  await page.getByLabel('파일 첨부').setInputFiles({ name: 'fixed.md', mimeType: 'text/markdown', buffer: Buffer.from('시설 점검 일정은 분기별로 담당자가 등록하고 부서별로 조회합니다.') });
  await page.getByRole('button', { name: '다시 첨부해 보내기' }).click();
  const followUp = page.getByRole('group', { name: /내 보완 답변/ });
  await expect(followUp).toContainText('revision 2', { timeout: 10_000 });
  await expect(followUp).toContainText('fixed.md'); // only the newly attached file; the carried-over one is not repeated
  await expect(followUp).not.toContainText('damaged.pdf');
  // The server keeps the damaged file with the new revision, so the choice stays open until it is excluded.
  await expect(page.getByRole('group', { name: '읽기 실패 파일' })).toContainText('damaged.pdf', { timeout: 30_000 });
  await expect(page.getByRole('group', { name: '읽기 실패 파일' }).locator('li')).toHaveCount(1);
  await page.getByRole('button', { name: '제외하고 진행' }).click();
  await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeVisible({ timeout: 200_000 });
  await a.ctx.close();
});

test('reviewer info request becomes a question bubble; the answer in the same composer is a supplement revision', async ({ browser }) => {
  test.setTimeout(300_000);
  const rq = await actor(browser, baseURL, 'requester'); const rv = await actor(browser, baseURL, 'reviewer');
  const id = await submitApi(rq, '사내 휴게실 예약 알림 기능을 추가해 주세요.');
  await waitJudged(rq, id);
  await pendingReview(rv, id);
  await rv.page.goto('/review');
  await rv.page.locator('nav[aria-label="검토 대기 목록"] button', { hasText: id }).click();
  await rv.page.getByLabel('결정 사유').fill('예약 대상 시설 목록이 필요합니다');
  await rv.page.getByRole('button', { name: '정보 요청', exact: true }).click();
  await expect(rv.page.getByRole('status')).toBeVisible();
  await rq.page.goto(`/?request_id=${id}`);
  const ask = rq.page.getByRole('group', { name: '보완 요청' });
  await expect(ask).toContainText('예약 대상 시설 목록이 필요합니다', { timeout: 30_000 });
  await shot(rq.page, 'info-request');
  await ask.getByRole('button', { name: '답변 입력하기' }).click();
  await expect(rq.page.getByLabel('요청 내용')).toBeFocused();
  await rq.page.getByLabel('요청 내용').fill('대상 시설은 휴게실 3곳입니다.');
  await rq.page.getByRole('button', { name: '답변 보내기' }).click();
  await expect(rq.page.getByRole('group', { name: /내 보완 답변/ })).toContainText('대상 시설은 휴게실 3곳입니다.');
  await expect.poll(async () => (await (await rq.api.get(`/api/requests/${id}`)).json()).revisions.length, { timeout: 30_000 }).toBe(2);
  await expect(rq.page.getByRole('group', { name: '보완 요청' })).toHaveCount(0, { timeout: 200_000 });
  await rq.ctx.close(); await rv.ctx.close();
});

test('files can be dropped on the composer and removed again', async ({ browser }) => {
  const a = await actor(browser, baseURL, 'requester'); const page = a.page;
  await page.goto('/');
  const transfer = await page.evaluateHandle(() => { const data = new DataTransfer(); data.items.add(new File(['x'], 'dropped.md', { type: 'text/markdown' })); return data; });
  const form = page.getByRole('form', { name: '일동이에게 요청' });
  await form.dispatchEvent('dragover', { dataTransfer: transfer });
  await expect(page.getByText('여기에 파일을 놓으면 첨부돼요')).toBeVisible();
  await form.dispatchEvent('drop', { dataTransfer: transfer });
  await expect(page.getByRole('list', { name: '첨부할 파일' })).toContainText('dropped.md');
  await page.getByRole('button', { name: 'dropped.md 첨부 제거' }).click();
  await expect(page.getByRole('list', { name: '첨부할 파일' })).toHaveCount(0);
  await a.ctx.close();
});

for (const width of [375, 520, 960, 1440]) {
  test(`responsive ${width}px: greeting and a restored result have no horizontal overflow; list panel folds below 960`, async ({ browser }) => {
    test.setTimeout(90_000);
    const a = await actor(browser, baseURL, 'requester'); const page = a.page;
    await page.setViewportSize({ width, height: 900 });
    const overflow = () => page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, inner: window.innerWidth, wide: [...document.querySelectorAll<HTMLElement>('main *')].filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1 && !el.closest('.table-scroll,pre')).slice(0, 4).map((el) => `${el.tagName}.${String(el.className).slice(0, 30)}`) }));
    await page.goto('/');
    await expect(page.getByRole('heading', { name: '안녕하세요, 일동이예요' })).toBeVisible();
    await shot(page, `greeting-${width}`);
    let m = await overflow(); expect(m.scroll, JSON.stringify(m)).toBeLessThanOrEqual(width);
    const list = (await (await a.api.get('/api/requests?limit=50')).json()).items as Array<{ id: string }>;
    test.skip(!list.length, 'no requests in this tenant yet');
    await page.goto(`/?request_id=${list[0].id}`);
    await expect(page.getByRole('group', { name: '분석 진행' })).toBeVisible({ timeout: 30_000 });
    await page.waitForTimeout(800);
    await shot(page, `conversation-${width}`);
    m = await overflow(); expect(m.scroll, JSON.stringify(m)).toBeLessThanOrEqual(width);
    const toggle = page.getByRole('button', { name: '내 요청' });
    if (width <= 960) {
      await expect(toggle).toBeVisible(); await expect(toggle).toHaveAttribute('aria-expanded', 'false');
      await expect(page.locator('.request-list')).toBeHidden(); // folded: the list lives in a sheet behind the 내 요청 button
      await toggle.click(); await expect(page.getByRole('dialog', { name: '내 요청 대화' })).toBeVisible(); await page.waitForTimeout(400); await shot(page, `list-open-${width}`);
      m = await overflow(); expect(m.scroll, JSON.stringify(m)).toBeLessThanOrEqual(width);
      await page.keyboard.press('Escape'); await expect(page.getByRole('dialog', { name: '내 요청 대화' })).toHaveCount(0);
    } else { await expect(toggle).toBeHidden(); await expect(page.locator('.request-list .list-body')).toBeVisible(); }
    const composer = await page.getByRole('form', { name: '일동이에게 요청' }).boundingBox();
    expect(composer!.x + composer!.width).toBeLessThanOrEqual(width + 1);
    await a.ctx.close();
  });
}

// CHAT-POLISH: fixed-height conversation. The page is exactly one screen tall at every width; the chat and the request list scroll inside it.
// Needs >= 30 requests in the tenant (seed them first, see artifacts/review/chat-polish/README.md).
const polishDir = resolve(process.cwd(), process.env.POLISH_SHOT_DIR || '../artifacts/review/chat-polish'); mkdirSync(polishDir, { recursive: true });
for (const size of [{ w: 1440, h: 900 }, { w: 960, h: 800 }, { w: 375, h: 812 }]) {
  test(`layout ${size.w}px: one screen tall, request list and chat scroll inside, composer pinned`, async ({ browser }) => {
    test.setTimeout(120_000);
    const a = await actor(browser, baseURL, 'requester'); const page = a.page;
    await page.setViewportSize({ width: size.w, height: size.h });
    await page.goto('/');
    const composerBox = async () => (await page.locator('form.composer').boundingBox())!;
    const metrics = () => page.evaluate(() => ({ docH: document.documentElement.scrollHeight, bodyH: document.body.scrollHeight, winH: window.innerHeight, docW: document.documentElement.scrollWidth, winW: window.innerWidth }));
    const record = async (label: string) => { const m = await metrics(); appendFileSync(join(polishDir, 'metrics.jsonl'), JSON.stringify({ browser: test.info().project.name, width: size.w, height: size.h, label, ...m }) + '\n'); return m; };
    const narrow = size.w <= 960;
    await expect(page.getByRole('heading', { name: '안녕하세요, 일동이예요' })).toBeVisible();
    const greetingBox = await composerBox();
    let first = await record('greeting');
    expect(first.docH, 'page is one screen tall').toBe(first.winH); expect(first.bodyH).toBeLessThanOrEqual(first.winH); expect(first.docW).toBeLessThanOrEqual(first.winW);
    expect(greetingBox.y + greetingBox.height).toBeLessThanOrEqual(first.winH);
    const middle = greetingBox.y + greetingBox.height / 2; expect(middle, 'empty conversation: the composer sits mid-screen with the greeting').toBeGreaterThan(first.winH * 0.3); expect(middle).toBeLessThan(first.winH * 0.75);
    await expect(page.getByRole('group', { name: '예시 요청' }).getByRole('button')).toHaveCount(3); // example chips below the composer
    if (narrow) await page.getByRole('button', { name: '내 요청' }).click();
    const list = narrow ? page.getByRole('dialog', { name: '내 요청 대화' }) : page.locator('.request-list');
    const rows = list.locator('.request-row');
    await expect.poll(() => rows.count()).toBeGreaterThanOrEqual(30);
    const title = rows.first().locator('.request-title');
    await expect(title).not.toHaveClass(/ui-skeleton/, { timeout: 15_000 });
    expect(await title.innerText()).not.toMatch(/^req_/);
    await expect(rows.first().locator('.status-dot')).toBeVisible(); await expect(list.getByRole('region', { name: /오늘|어제|지난 7일|지난 30일|\d+월/ }).first()).toBeVisible(); // status dot + day groups
    const style = await title.evaluate((el) => { const c = getComputedStyle(el); return { overflow: c.overflow, textOverflow: c.textOverflow, whiteSpace: c.whiteSpace }; });
    expect(style).toEqual({ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' });
    const scroller = list.locator('.list-scroll');
    if (!narrow) {
      const listBox = await page.locator('.request-list').boundingBox();
      expect(listBox!.height).toBeLessThanOrEqual(first.winH); // the list never stretches the page
      const dims = await scroller.evaluate((el) => ({ scroll: el.scrollHeight, client: el.clientHeight, overflowY: getComputedStyle(el).overflowY }));
      expect(dims.scroll).toBeGreaterThan(dims.client); expect(dims.overflowY).toBe('auto');
    }
    await page.waitForTimeout(400); await page.screenshot({ path: join(polishDir, `${test.info().project.name}-list-${size.w}.png`), fullPage: true });
    const after = await record('list-open'); expect(after.docH).toBe(after.winH); expect(after.docW).toBeLessThanOrEqual(after.winW);
    await rows.filter({ has: page.getByRole('img', { name: '검토 대기' }) }).first().click(); // a judged request: its summary card lands in the conversation
    await expect(page.getByRole('group', { name: '일동이의 답변' })).toBeVisible({ timeout: 30_000 });
    await expect(page.locator('.chat-row .judgment-card')).toHaveCount(4);
    await expect(page.getByRole('button', { name: '자세히 보기' })).toBeVisible();
    await page.waitForTimeout(500);
    const conv = await record('conversation'); expect(conv.docH).toBe(conv.winH); expect(conv.docW).toBeLessThanOrEqual(conv.winW);
    const convBox = await composerBox();
    expect(conv.winH - (convBox.y + convBox.height), 'composer pinned near the bottom edge').toBeLessThan(40);
    expect(await page.locator('.chat-scroll').evaluate((el) => getComputedStyle(el).overflowY)).toBe('auto');
    await page.screenshot({ path: join(polishDir, `${test.info().project.name}-conversation-${size.w}.png`), fullPage: true });
    await page.getByRole('button', { name: '자세히 보기' }).click();
    const drawer = page.getByRole('dialog', { name: '판단 상세' });
    await expect(drawer).toBeVisible(); await expect(drawer.getByRole('heading', { name: '업무 분담' })).toBeVisible();
    await page.waitForTimeout(500); await page.screenshot({ path: join(polishDir, `${test.info().project.name}-detail-${size.w}.png`), fullPage: true });
    const detail = await record('detail'); expect(detail.docH).toBe(detail.winH); expect(detail.docW).toBeLessThanOrEqual(detail.winW);
    await page.keyboard.press('Escape'); await expect(drawer).toHaveCount(0);
    const closed = await composerBox(); expect(Math.abs(closed.y - convBox.y), 'composer does not move when the sheet opens and closes').toBeLessThanOrEqual(1);
    await a.ctx.close();
  });
}

test('reduced motion: bubbles and typing dots do not animate', async ({ browser }) => {
  const a = await actor(browser, baseURL, 'requester'); const page = a.page;
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect.poll(() => page.locator('.request-row').count()).toBeGreaterThan(0);
  await page.locator('.request-row').first().click();
  const row = page.locator('.chat-row').first(); await expect(row).toBeVisible();
  expect(await row.evaluate((el) => parseFloat(getComputedStyle(el).animationDuration))).toBeLessThan(0.01);
  await a.ctx.close();
});

test('scrolled up while the answer arrives: a "새 메시지" pill appears instead of a jump, and takes you down', async ({ browser }) => {
  test.setTimeout(240_000);
  const a = await actor(browser, baseURL, 'requester'); const page = a.page;
  await page.setViewportSize({ width: 390, height: 520 });
  await page.goto('/');
  await page.getByLabel('요청 내용').fill('사내 도서 대여 현황을 한눈에 볼 수 있는 화면이 필요합니다.');
  await page.getByLabel('요청 내용').press('Enter'); // Enter sends
  await expect(page.getByRole('group', { name: '내가 보낸 요청' })).toBeVisible();
  await expect(page.getByRole('group', { name: '일동이가 입력 중' })).toBeVisible({ timeout: 30_000 });
  const scroller = page.locator('.chat-scroll');
  const reachable = await scroller.evaluate((el) => { el.scrollTop = 0; el.dispatchEvent(new Event('scroll')); return el.scrollHeight - el.clientHeight; });
  expect(reachable, 'conversation is taller than the chat area').toBeGreaterThan(120);
  const pill = page.getByRole('button', { name: /새 메시지/ });
  await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeAttached({ timeout: 200_000 });
  await expect(pill).toBeVisible();
  expect(await scroller.evaluate((el) => el.scrollTop), 'reading position is kept').toBeLessThan(120);
  await pill.click();
  await expect.poll(() => scroller.evaluate((el) => el.scrollHeight - el.scrollTop - el.clientHeight), { timeout: 5000 }).toBeLessThan(80);
  await expect(pill).toHaveCount(0);
  await a.ctx.close();
});
