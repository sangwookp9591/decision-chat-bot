import { execFileSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { expect, test, type BrowserContext } from '@playwright/test';

// Real API/Neo4j journey with deterministic persisted human correction fixtures.
// This tests the learning contract without spending model calls on fixture creation.
function python(code: string, tenant: string) {
  execFileSync('../backend/.venv/bin/python', ['-c', code, tenant], { cwd: process.cwd(), timeout: 60_000 });
}
const seed = `
import asyncio, sys
sys.path[:0] = ['../backend', '../backend/tests/acceptance']
from provision import provision
from jevtriage.db.tx import write_tx
from jevtriage.db.driver import close_driver
async def main():
    tenant = sys.argv[1]
    await provision((tenant,))
    async def op(tx):
        await (await tx.run('''UNWIND range(1,3) AS i
CREATE (q:Request {tenant_id:$tenant,id:$tenant+'-req_'+toString(i),created_by:'author',org_ids:[$org]})
CREATE (j:Judgment {tenant_id:$tenant,id:$tenant+'-jdg_'+toString(i),run_id:$tenant+'-run_'+toString(i),request_id:q.id,revision_id:$tenant+'-rev_'+toString(i),created_at:datetime(),ai_need:'필요',feasibility:'가능',urgency:'일반',lead_org:'IT팀'})
CREATE (h:ReviewDecision {tenant_id:$tenant,id:$tenant+'-dec_'+toString(i),run_id:j.run_id,action:'approve_with_changes'})
CREATE (c:Correction {tenant_id:$tenant,id:$tenant+'-cor_'+toString(i),request_id:q.id,run_id:j.run_id,field:'ai_need',ai_value:'"필요"',corrected_value:'"혼합"',corrected_by:'reviewer',corrected_at:datetime()})
CREATE (h)-[:RECORDED]->(c)''', tenant=tenant,org=tenant+'-it')).consume()
    await write_tx(tenant,op)
    await close_driver()
asyncio.run(main())
`;
const cleanup = `
import asyncio,sys
sys.path.insert(0,'../backend')
from jevtriage.db.tx import write_tx
from jevtriage.db.driver import close_driver
async def main():
    async def op(tx):
        await (await tx.run('MATCH (n {tenant_id:$tenant}) DETACH DELETE n',tenant=sys.argv[1])).consume()
    await write_tx(sys.argv[1],op)
    await close_driver()
asyncio.run(main())
`;
async function login(ctx: BrowserContext, tenant: string, role: string) {
  const r = await ctx.request.post('/api/auth/login', { data: { email: `${role}@${tenant}.dev`, password: 'dev-only-change-me' } });
  expect(r.ok(), await r.text()).toBeTruthy();
}

test('human proposal → approval → shadow → publication; scoped readers cannot mutate', async ({ browser, baseURL }) => {
  test.setTimeout(120_000);
  const tenant = `t-human-${randomUUID().replaceAll('-', '')}`;
  const contexts: BrowserContext[] = [];
  try {
    python(seed, tenant);
    const reviewer = await browser.newContext({ baseURL }); contexts.push(reviewer);
    await login(reviewer, tenant, 'reviewer');
    const page = await reviewer.newPage();
    await page.goto('/learning');
    await page.getByRole('button', { name: '사람 후보 제안', exact: true }).click();
    const form = page.getByRole('form', { name: '사람 후보 제안' });
    await expect(form).toContainText('지원하지 않습니다');
    await form.getByLabel('제안 값', { exact: true }).selectOption('혼합');
    for (const id of ['cor_1', 'cor_2', 'cor_3']) await form.getByLabel(`지지 ${tenant}-${id}`, { exact: true }).check();
    await form.getByLabel('제안 범위', { exact: true }).fill(JSON.stringify({ all: [{ requester_org: `${tenant}-it` }] }));
    await form.getByLabel('제안 사유', { exact: true }).fill('세 건의 사람 수정에 근거한 범위 제한 제안');
    await form.getByRole('button', { name: '후보 제안 저장' }).click();
    await expect(page.getByRole('status')).toContainText('사람 후보를 제안했습니다');
    await expect(page.getByRole('table', { name: '근거 수정 기록' })).toContainText(`${tenant}-req_3`);
    const candidate = new URL(page.url()).searchParams.get('candidate_id');
    expect(candidate).toBeTruthy();
    await expect(page.getByRole('button', { name: '승인', exact: true })).toBeDisabled();

    const admin = await browser.newContext({ baseURL }); contexts.push(admin);
    await login(admin, tenant, 'rule_admin');
    const adminPage = await admin.newPage();
    await adminPage.goto(`/learning?candidate_id=${candidate}`);
    await adminPage.getByLabel('결정 사유').fill('사람 지지 표본과 조직 범위 확인 후 승인');
    await adminPage.getByRole('button', { name: '승인', exact: true }).click();
    await expect(adminPage.getByRole('status')).toContainText('규칙 버전');
    await expect(adminPage.getByRole('button', { name: '게시', exact: true })).toBeDisabled();
    await adminPage.getByRole('button', { name: '검증 실행' }).click();
    await expect(adminPage.getByRole('status')).toContainText('비교 검증을 실행했습니다');
    await expect(adminPage.getByRole('button', { name: '검증 실행' })).toBeEnabled();
    await expect(adminPage.getByRole('region', { name: '비교 검증' })).toContainText('사람 확정 정답 3건');
    await expect(adminPage.getByRole('region', { name: '비교 검증' })).toContainText('부작용 0건');
    await adminPage.getByLabel('결정 사유').fill('섀도 검증 부작용 없음 확인');
    await adminPage.getByRole('button', { name: '검증 완료 처리' }).click();
    await expect(adminPage.getByRole('status')).toContainText('검증 완료로 표시');
    await adminPage.getByLabel('결정 사유').fill('섀도 검증 완료 후 조직 범위 내 게시');
    await adminPage.getByRole('button', { name: '게시', exact: true }).click();
    await expect(adminPage.getByRole('status')).toContainText('새 Config 버전');
    await expect(adminPage.getByRole('region', { name: '게시 후 관찰' })).toContainText('미확정');

    await page.reload();
    await expect(page.getByRole('region', { name: '게시 후 관찰' })).toContainText('사람 확정 정답 표본 수');
    await expect(page.getByRole('button', { name: '게시', exact: true })).toBeDisabled();
    const operator = await browser.newContext({ baseURL }); contexts.push(operator);
    await login(operator, tenant, 'operator');
    const opPage = await operator.newPage();
    await opPage.goto(`/learning?candidate_id=${candidate}`);
    await expect(opPage.getByRole('region', { name: '게시 후 관찰' })).toContainText('미확정');
    await expect(opPage.getByRole('button', { name: '사람 후보 제안', exact: true })).toHaveCount(0);
    const outsider = await browser.newContext({ baseURL }); contexts.push(outsider);
    await login(outsider, tenant, 'outsider_reviewer');
    expect((await outsider.request.get('/api/learning/rules/R-AI_NEED-01')).status()).toBe(404);
    expect((await outsider.request.get('/api/learning/rules/R-AI_NEED-01/effects')).status()).toBe(404);
  } finally {
    await Promise.allSettled(contexts.map((ctx) => ctx.close()));
    python(cleanup, tenant);
  }
});
