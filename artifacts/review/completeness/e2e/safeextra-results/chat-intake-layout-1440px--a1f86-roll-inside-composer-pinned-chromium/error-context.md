# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: chat-intake.spec.ts >> layout 1440px: one screen tall, request list and chat scroll inside, composer pinned
- Location: artifacts/review/completeness/scratch/suite/chat-intake.spec.ts:173:7

# Error details

```
Error: expect(received).toBeGreaterThanOrEqual(expected)

Expected: >= 30
Received:    5

Call Log:
- Timeout 5000ms exceeded while waiting on the predicate
```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - generic [ref=e5]: Jev Triage
    - navigation "주 메뉴" [ref=e6]:
      - link "요청 접수" [ref=e7] [cursor=pointer]:
        - /url: /
      - link "검토 대기" [ref=e8] [cursor=pointer]:
        - /url: /review
      - link "업무" [ref=e9] [cursor=pointer]:
        - /url: /tasks
      - link "실행 관찰" [ref=e10] [cursor=pointer]:
        - /url: /observatory
      - link "판단 맵" [ref=e11] [cursor=pointer]:
        - /url: /judgment-map
      - link "규칙 학습" [ref=e12] [cursor=pointer]:
        - /url: /learning
      - link "모니터링" [ref=e13] [cursor=pointer]:
        - /url: /monitoring
      - link "정책" [ref=e14] [cursor=pointer]:
        - /url: /policy
      - link "평가 라벨" [ref=e15] [cursor=pointer]:
        - /url: /evaluation
    - generic [ref=e16]:
      - strong [ref=e17]: usr_t-audit-e2e-1005_requester
      - generic [ref=e18]: 요청자
      - button "로그아웃" [ref=e19] [cursor=pointer]
  - generic [ref=e20]:
    - banner [ref=e21]:
      - generic [ref=e22]: 의사결정 지원
      - generic [ref=e23]:
        - generic [ref=e24]: usr_t-audit-e2e-1005_requester · 요청자
        - generic [ref=e25]: live
        - button "로그아웃" [ref=e26] [cursor=pointer]
    - main [ref=e27]:
      - generic [ref=e28]:
        - complementary "대화 목록" [ref=e29]:
          - generic [ref=e30]:
            - generic [ref=e31]:
              - button "새 요청" [ref=e32] [cursor=pointer]
              - heading "내 요청 대화" [level=2] [ref=e35]
            - region "오늘" [ref=e37]:
              - heading "오늘" [level=3] [ref=e38]
              - button "완료 제목 없는 요청 audit_map_req" [ref=e39] [cursor=pointer]:
                - img "완료" [ref=e40]
                - generic [ref=e41]: 제목 없는 요청
                - code [aria-hidden] [ref=e42]: audit_ma
                - generic [ref=e43]: audit_map_req
              - button "검토 대기 분기별 시설 점검 일정을 검색하고 담당자별로 확인하고 싶습니다. req_33a60302a76c4b96906b01cdf11aab4e" [ref=e44] [cursor=pointer]:
                - img "검토 대기" [ref=e45]
                - generic [ref=e46]: 분기별 시설 점검 일정을 검색하고 담당자별로 확인하고 싶습니다.
                - code [aria-hidden] [ref=e47]: req_33a6
                - generic [ref=e48]: req_33a60302a76c4b96906b01cdf11aab4e
              - button "배정 완료 출하 지시가 멈췄어요. req_3503948c4b87404cba4714536567406e" [ref=e49] [cursor=pointer]:
                - img "배정 완료" [ref=e50]
                - generic [ref=e51]: 출하 지시가 멈췄어요.
                - code [aria-hidden] [ref=e52]: req_3503
                - generic [ref=e53]: req_3503948c4b87404cba4714536567406e
              - button "취소됨 사내 회의실 예약 도구를 도입하려고 합니다. req_f7ce2a90cbaf4292ab72e7ddb7872d77" [ref=e54] [cursor=pointer]:
                - img "취소됨" [ref=e55]
                - generic [ref=e56]: 사내 회의실 예약 도구를 도입하려고 합니다.
                - code [aria-hidden] [ref=e57]: req_f7ce
                - generic [ref=e58]: req_f7ce2a90cbaf4292ab72e7ddb7872d77
              - button "반려됨 SAP에서 내려받은 매출 CSV를 월별로 집계해 화면에 보여 주세요. req_7e2fe8f1d23f4cff9d0510fbbb470984" [ref=e59] [cursor=pointer]:
                - img "반려됨" [ref=e60]
                - generic [ref=e61]: SAP에서 내려받은 매출 CSV를 월별로 집계해 화면에 보여 주세요.
                - code [aria-hidden] [ref=e62]: req_7e2f
                - generic [ref=e63]: req_7e2fe8f1d23f4cff9d0510fbbb470984
        - generic [ref=e64]:
          - heading "일동이와 요청 접수" [level=1] [ref=e66]
          - generic [ref=e67]:
            - log "일동이와의 대화" [ref=e70]:
              - region "일동이 인사" [ref=e71]:
                - heading "안녕하세요, 일동이예요" [level=2] [ref=e73]
                - paragraph [ref=e74]: 무엇을 도와드릴까요? 업무 요청을 적거나 문서를 올려 주세요.AI·일반 개발·사람이 맡을 일을 나눠 드려요.
            - form "일동이에게 요청" [ref=e76]:
              - generic [ref=e77]:
                - generic "파일 첨부" [ref=e78] [cursor=pointer]:
                  - button "파일 첨부" [ref=e81]
                - generic [ref=e82]: 요청 내용
                - textbox "요청 내용" [ref=e83]:
                  - /placeholder: 필요한 업무와 해결하려는 문제를 적어 주세요
                - button "요청 보내기" [disabled] [ref=e84]
              - paragraph [ref=e87]: PDF · DOCX · MD, 최대 5개 · 파일당 10 MiB · 합계 25 MiB · Enter로 보내기 · Shift + Enter로 줄바꿈
            - group "예시 요청" [ref=e88]:
              - generic [ref=e89]: 이렇게 요청해 보세요
              - button "SAP 매출 CSV를 월별로 집계해 화면에 보여 주세요" [ref=e90] [cursor=pointer]
              - button "병원별 판매량으로 다음 달 수요를 예측하고 싶어요" [ref=e91] [cursor=pointer]
              - button "출하 지시가 멈췄어요. 오늘 마감이에요" [ref=e92] [cursor=pointer]
```

# Test source

```ts
  92  |   await expect(page.getByRole('group', { name: '읽기 실패 파일' })).toContainText('damaged.pdf', { timeout: 30_000 });
  93  |   await expect(page.getByRole('group', { name: '읽기 실패 파일' }).locator('li')).toHaveCount(1);
  94  |   await page.getByRole('button', { name: '제외하고 진행' }).click();
  95  |   await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeVisible({ timeout: 200_000 });
  96  |   await a.ctx.close();
  97  | });
  98  | 
  99  | test('reviewer info request becomes a question bubble; the answer in the same composer is a supplement revision', async ({ browser }) => {
  100 |   test.setTimeout(300_000);
  101 |   const rq = await actor(browser, baseURL, 'requester'); const rv = await actor(browser, baseURL, 'reviewer');
  102 |   const id = await submitApi(rq, '사내 휴게실 예약 알림 기능을 추가해 주세요.');
  103 |   await waitJudged(rq, id);
  104 |   await pendingReview(rv, id);
  105 |   await rv.page.goto('/review');
  106 |   await rv.page.locator('nav[aria-label="검토 대기 목록"] button', { hasText: id }).click();
  107 |   await rv.page.getByLabel('결정 사유').fill('예약 대상 시설 목록이 필요합니다');
  108 |   await rv.page.getByRole('button', { name: '정보 요청', exact: true }).click();
  109 |   await expect(rv.page.getByRole('status')).toBeVisible();
  110 |   await rq.page.goto(`/?request_id=${id}`);
  111 |   const ask = rq.page.getByRole('group', { name: '보완 요청' });
  112 |   await expect(ask).toContainText('예약 대상 시설 목록이 필요합니다', { timeout: 30_000 });
  113 |   await shot(rq.page, 'info-request');
  114 |   await ask.getByRole('button', { name: '답변 입력하기' }).click();
  115 |   await expect(rq.page.getByLabel('요청 내용')).toBeFocused();
  116 |   await rq.page.getByLabel('요청 내용').fill('대상 시설은 휴게실 3곳입니다.');
  117 |   await rq.page.getByRole('button', { name: '답변 보내기' }).click();
  118 |   await expect(rq.page.getByRole('group', { name: /내 보완 답변/ })).toContainText('대상 시설은 휴게실 3곳입니다.');
  119 |   await expect.poll(async () => (await (await rq.api.get(`/api/requests/${id}`)).json()).revisions.length, { timeout: 30_000 }).toBe(2);
  120 |   await expect(rq.page.getByRole('group', { name: '보완 요청' })).toHaveCount(0, { timeout: 200_000 });
  121 |   await rq.ctx.close(); await rv.ctx.close();
  122 | });
  123 | 
  124 | test('files can be dropped on the composer and removed again', async ({ browser }) => {
  125 |   const a = await actor(browser, baseURL, 'requester'); const page = a.page;
  126 |   await page.goto('/');
  127 |   const transfer = await page.evaluateHandle(() => { const data = new DataTransfer(); data.items.add(new File(['x'], 'dropped.md', { type: 'text/markdown' })); return data; });
  128 |   const form = page.getByRole('form', { name: '일동이에게 요청' });
  129 |   await form.dispatchEvent('dragover', { dataTransfer: transfer });
  130 |   await expect(page.getByText('여기에 파일을 놓으면 첨부돼요')).toBeVisible();
  131 |   await form.dispatchEvent('drop', { dataTransfer: transfer });
  132 |   await expect(page.getByRole('list', { name: '첨부할 파일' })).toContainText('dropped.md');
  133 |   await page.getByRole('button', { name: 'dropped.md 첨부 제거' }).click();
  134 |   await expect(page.getByRole('list', { name: '첨부할 파일' })).toHaveCount(0);
  135 |   await a.ctx.close();
  136 | });
  137 | 
  138 | for (const width of [375, 520, 960, 1440]) {
  139 |   test(`responsive ${width}px: greeting and a restored result have no horizontal overflow; list panel folds below 960`, async ({ browser }) => {
  140 |     test.setTimeout(90_000);
  141 |     const a = await actor(browser, baseURL, 'requester'); const page = a.page;
  142 |     await page.setViewportSize({ width, height: 900 });
  143 |     const overflow = () => page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, inner: window.innerWidth, wide: [...document.querySelectorAll<HTMLElement>('main *')].filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1 && !el.closest('.table-scroll,pre')).slice(0, 4).map((el) => `${el.tagName}.${String(el.className).slice(0, 30)}`) }));
  144 |     await page.goto('/');
  145 |     await expect(page.getByRole('heading', { name: '안녕하세요, 일동이예요' })).toBeVisible();
  146 |     await shot(page, `greeting-${width}`);
  147 |     let m = await overflow(); expect(m.scroll, JSON.stringify(m)).toBeLessThanOrEqual(width);
  148 |     const list = (await (await a.api.get('/api/requests?limit=50')).json()).items as Array<{ id: string }>;
  149 |     test.skip(!list.length, 'no requests in this tenant yet');
  150 |     await page.goto(`/?request_id=${list[0].id}`);
  151 |     await expect(page.getByRole('group', { name: '분석 진행' })).toBeVisible({ timeout: 30_000 });
  152 |     await page.waitForTimeout(800);
  153 |     await shot(page, `conversation-${width}`);
  154 |     m = await overflow(); expect(m.scroll, JSON.stringify(m)).toBeLessThanOrEqual(width);
  155 |     const toggle = page.getByRole('button', { name: '내 요청' });
  156 |     if (width <= 960) {
  157 |       await expect(toggle).toBeVisible(); await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  158 |       await expect(page.locator('.request-list')).toBeHidden(); // folded: the list lives in a sheet behind the 내 요청 button
  159 |       await toggle.click(); await expect(page.getByRole('dialog', { name: '내 요청 대화' })).toBeVisible(); await page.waitForTimeout(400); await shot(page, `list-open-${width}`);
  160 |       m = await overflow(); expect(m.scroll, JSON.stringify(m)).toBeLessThanOrEqual(width);
  161 |       await page.keyboard.press('Escape'); await expect(page.getByRole('dialog', { name: '내 요청 대화' })).toHaveCount(0);
  162 |     } else { await expect(toggle).toBeHidden(); await expect(page.locator('.request-list .list-body')).toBeVisible(); }
  163 |     const composer = await page.getByRole('form', { name: '일동이에게 요청' }).boundingBox();
  164 |     expect(composer!.x + composer!.width).toBeLessThanOrEqual(width + 1);
  165 |     await a.ctx.close();
  166 |   });
  167 | }
  168 | 
  169 | // CHAT-POLISH: fixed-height conversation. The page is exactly one screen tall at every width; the chat and the request list scroll inside it.
  170 | // Needs >= 30 requests in the tenant (seed them first, see artifacts/review/chat-polish/README.md).
  171 | const polishDir = resolve(process.cwd(), process.env.POLISH_SHOT_DIR || '../artifacts/review/chat-polish'); mkdirSync(polishDir, { recursive: true });
  172 | for (const size of [{ w: 1440, h: 900 }, { w: 960, h: 800 }, { w: 375, h: 812 }]) {
  173 |   test(`layout ${size.w}px: one screen tall, request list and chat scroll inside, composer pinned`, async ({ browser }) => {
  174 |     test.setTimeout(120_000);
  175 |     const a = await actor(browser, baseURL, 'requester'); const page = a.page;
  176 |     await page.setViewportSize({ width: size.w, height: size.h });
  177 |     await page.goto('/');
  178 |     const composerBox = async () => (await page.locator('form.composer').boundingBox())!;
  179 |     const metrics = () => page.evaluate(() => ({ docH: document.documentElement.scrollHeight, bodyH: document.body.scrollHeight, winH: window.innerHeight, docW: document.documentElement.scrollWidth, winW: window.innerWidth }));
  180 |     const record = async (label: string) => { const m = await metrics(); appendFileSync(join(polishDir, 'metrics.jsonl'), JSON.stringify({ browser: test.info().project.name, width: size.w, height: size.h, label, ...m }) + '\n'); return m; };
  181 |     const narrow = size.w <= 960;
  182 |     await expect(page.getByRole('heading', { name: '안녕하세요, 일동이예요' })).toBeVisible();
  183 |     const greetingBox = await composerBox();
  184 |     let first = await record('greeting');
  185 |     expect(first.docH, 'page is one screen tall').toBe(first.winH); expect(first.bodyH).toBeLessThanOrEqual(first.winH); expect(first.docW).toBeLessThanOrEqual(first.winW);
  186 |     expect(greetingBox.y + greetingBox.height).toBeLessThanOrEqual(first.winH);
  187 |     const middle = greetingBox.y + greetingBox.height / 2; expect(middle, 'empty conversation: the composer sits mid-screen with the greeting').toBeGreaterThan(first.winH * 0.3); expect(middle).toBeLessThan(first.winH * 0.75);
  188 |     await expect(page.getByRole('group', { name: '예시 요청' }).getByRole('button')).toHaveCount(3); // example chips below the composer
  189 |     if (narrow) await page.getByRole('button', { name: '내 요청' }).click();
  190 |     const list = narrow ? page.getByRole('dialog', { name: '내 요청 대화' }) : page.locator('.request-list');
  191 |     const rows = list.locator('.request-row');
> 192 |     await expect.poll(() => rows.count()).toBeGreaterThanOrEqual(30);
      |                                           ^ Error: expect(received).toBeGreaterThanOrEqual(expected)
  193 |     const title = rows.first().locator('.request-title');
  194 |     await expect(title).not.toHaveClass(/ui-skeleton/, { timeout: 15_000 });
  195 |     expect(await title.innerText()).not.toMatch(/^req_/);
  196 |     await expect(rows.first().locator('.status-dot')).toBeVisible(); await expect(list.getByRole('region', { name: /오늘|어제|지난 7일|지난 30일|\d+월/ }).first()).toBeVisible(); // status dot + day groups
  197 |     const style = await title.evaluate((el) => { const c = getComputedStyle(el); return { overflow: c.overflow, textOverflow: c.textOverflow, whiteSpace: c.whiteSpace }; });
  198 |     expect(style).toEqual({ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' });
  199 |     const scroller = list.locator('.list-scroll');
  200 |     if (!narrow) {
  201 |       const listBox = await page.locator('.request-list').boundingBox();
  202 |       expect(listBox!.height).toBeLessThanOrEqual(first.winH); // the list never stretches the page
  203 |       const dims = await scroller.evaluate((el) => ({ scroll: el.scrollHeight, client: el.clientHeight, overflowY: getComputedStyle(el).overflowY }));
  204 |       expect(dims.scroll).toBeGreaterThan(dims.client); expect(dims.overflowY).toBe('auto');
  205 |     }
  206 |     await page.waitForTimeout(400); await page.screenshot({ path: join(polishDir, `${test.info().project.name}-list-${size.w}.png`), fullPage: true });
  207 |     const after = await record('list-open'); expect(after.docH).toBe(after.winH); expect(after.docW).toBeLessThanOrEqual(after.winW);
  208 |     await rows.filter({ has: page.getByRole('img', { name: '검토 대기' }) }).first().click(); // a judged request: its summary card lands in the conversation
  209 |     await expect(page.getByRole('group', { name: '일동이의 답변' })).toBeVisible({ timeout: 30_000 });
  210 |     await expect(page.locator('.chat-row .judgment-card')).toHaveCount(4);
  211 |     await expect(page.getByRole('button', { name: '자세히 보기' })).toBeVisible();
  212 |     await page.waitForTimeout(500);
  213 |     const conv = await record('conversation'); expect(conv.docH).toBe(conv.winH); expect(conv.docW).toBeLessThanOrEqual(conv.winW);
  214 |     const convBox = await composerBox();
  215 |     expect(conv.winH - (convBox.y + convBox.height), 'composer pinned near the bottom edge').toBeLessThan(40);
  216 |     expect(await page.locator('.chat-scroll').evaluate((el) => getComputedStyle(el).overflowY)).toBe('auto');
  217 |     await page.screenshot({ path: join(polishDir, `${test.info().project.name}-conversation-${size.w}.png`), fullPage: true });
  218 |     await page.getByRole('button', { name: '자세히 보기' }).click();
  219 |     const drawer = page.getByRole('dialog', { name: '판단 상세' });
  220 |     await expect(drawer).toBeVisible(); await expect(drawer.getByRole('heading', { name: '업무 분담' })).toBeVisible();
  221 |     await page.waitForTimeout(500); await page.screenshot({ path: join(polishDir, `${test.info().project.name}-detail-${size.w}.png`), fullPage: true });
  222 |     const detail = await record('detail'); expect(detail.docH).toBe(detail.winH); expect(detail.docW).toBeLessThanOrEqual(detail.winW);
  223 |     await page.keyboard.press('Escape'); await expect(drawer).toHaveCount(0);
  224 |     const closed = await composerBox(); expect(Math.abs(closed.y - convBox.y), 'composer does not move when the sheet opens and closes').toBeLessThanOrEqual(1);
  225 |     await a.ctx.close();
  226 |   });
  227 | }
  228 | 
  229 | test('reduced motion: bubbles and typing dots do not animate', async ({ browser }) => {
  230 |   const a = await actor(browser, baseURL, 'requester'); const page = a.page;
  231 |   await page.emulateMedia({ reducedMotion: 'reduce' });
  232 |   await page.goto('/');
  233 |   await expect.poll(() => page.locator('.request-row').count()).toBeGreaterThan(0);
  234 |   await page.locator('.request-row').first().click();
  235 |   const row = page.locator('.chat-row').first(); await expect(row).toBeVisible();
  236 |   expect(await row.evaluate((el) => parseFloat(getComputedStyle(el).animationDuration))).toBeLessThan(0.01);
  237 |   await a.ctx.close();
  238 | });
  239 | 
  240 | test('scrolled up while the answer arrives: a "새 메시지" pill appears instead of a jump, and takes you down', async ({ browser }) => {
  241 |   test.setTimeout(240_000);
  242 |   const a = await actor(browser, baseURL, 'requester'); const page = a.page;
  243 |   await page.setViewportSize({ width: 390, height: 520 });
  244 |   await page.goto('/');
  245 |   await page.getByLabel('요청 내용').fill('사내 도서 대여 현황을 한눈에 볼 수 있는 화면이 필요합니다.');
  246 |   await page.getByLabel('요청 내용').press('Enter'); // Enter sends
  247 |   await expect(page.getByRole('group', { name: '내가 보낸 요청' })).toBeVisible();
  248 |   await expect(page.getByRole('group', { name: '일동이가 입력 중' })).toBeVisible({ timeout: 30_000 });
  249 |   const scroller = page.locator('.chat-scroll');
  250 |   const reachable = await scroller.evaluate((el) => { el.scrollTop = 0; el.dispatchEvent(new Event('scroll')); return el.scrollHeight - el.clientHeight; });
  251 |   expect(reachable, 'conversation is taller than the chat area').toBeGreaterThan(120);
  252 |   const pill = page.getByRole('button', { name: /새 메시지/ });
  253 |   await expect(page.locator('.result-stack:not(.provisional-result)').getByRole('heading', { name: '판단 결과', exact: true })).toBeAttached({ timeout: 200_000 });
  254 |   await expect(pill).toBeVisible();
  255 |   expect(await scroller.evaluate((el) => el.scrollTop), 'reading position is kept').toBeLessThan(120);
  256 |   await pill.click();
  257 |   await expect.poll(() => scroller.evaluate((el) => el.scrollHeight - el.scrollTop - el.clientHeight), { timeout: 5000 }).toBeLessThan(80);
  258 |   await expect(pill).toHaveCount(0);
  259 |   await a.ctx.close();
  260 | });
  261 | 
```