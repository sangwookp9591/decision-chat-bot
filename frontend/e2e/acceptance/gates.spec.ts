import { execFileSync } from 'node:child_process';
import { expect, test } from '@playwright/test';
import { actor, outDir, shot, tenant, type Actor } from './helpers';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * T21-gates UI: G05 (auto-assigned tasks shown in 업무) and G06 (Neo4j relationships == 업무 Topology + 업무 screens).
 * Reads the stored-state snapshot that backend/tests/acceptance/acc_e_gates.py wrote (ACC_RECORDS=<records.jsonl>;
 * the Cypher results are in `g05_auto_assign` / `g06_graph`), then compares what the screens show.
 * When no snapshot is supplied, prepare a real auto-assigned request with scripts/e2e/gates.py.
 */
test.describe.configure({ mode: 'serial' });
test.setTimeout(180_000);

const gateTenant = `${tenant}g`;
const orgLabel = (id: string) => (id.endsWith('-it') ? 'IT팀' : id.endsWith('-ai') ? 'AI팀' : id.endsWith('-business') ? '현업' : id);
const orgName = (id: string) => id.split('-').pop() as string;
const evidence: Record<string, unknown> = {};
const keep = (k: string, v: unknown) => { evidence[k] = v; writeFileSync(join(outDir, 'gates-ui-evidence.json'), JSON.stringify(evidence, null, 2)); };

function records(): Record<string, any> {
  const path = process.env.ACC_RECORDS || '';
  if (!path) throw new Error('ACC_RECORDS is not set: run backend/tests/acceptance/acc_e_gates.py first (make test-acceptance does)');
  const out: Record<string, any> = {};
  for (const line of readFileSync(path, 'utf8').split('\n').filter(Boolean)) { const r = JSON.parse(line); out[r.name] = r.data; }
  return out;
}

let rv: Actor, rq: Actor;
test.beforeAll(async ({ browser }, info) => {
  if (!process.env.ACC_RECORDS || !existsSync(process.env.ACC_RECORDS)) {
    process.env.ACC_RECORDS = join(outDir, 'gate-records.jsonl');
    execFileSync('../backend/.venv/bin/python', ['../scripts/e2e/gates.py', process.env.ACC_RECORDS], { timeout: 120_000 });
  }
  const base = info.project.use.baseURL as string;
  rv = await actor(browser, base, 'reviewer', gateTenant);
  rq = await actor(browser, base, 'requester', gateTenant);
});

test('G05 auto-assigned requests: stored Assignment/Task/HAS_TASK/ASSIGNED_TO/PRECEDES appear on the 업무 screen', async () => {
  const rec = records().g05_auto_assign;
  expect(rec, 'g05_auto_assign record').toBeTruthy();
  const auto = Object.values(rec.auto_assigned || {}) as any[];
  expect(auto.length, 'fixture must contain a real automatic assignment').toBeGreaterThan(0);
  const shown: Record<string, unknown> = {};
  await rv.page.goto('/tasks');
  for (const a of auto) {
    const apiTasks = (await (await rv.api.get(`/api/tasks?request_id=${a.request_id}`)).json()).tasks as any[];
    expect(apiTasks.map((t) => t.id).sort()).toEqual([...a.tasks].sort()); // API == Cypher snapshot
    await rv.page.getByRole('button', { name: '새로고침' }).click();
    for (const t of apiTasks) {
      const row = rv.page.locator('.task-list button', { hasText: t.id });
      await expect(row).toBeVisible();
      await expect(row).toContainText(t.title);
      await expect(row).toContainText(`${t.request_id}`);
      await expect(row).toContainText(`주관 ${t.lead_org}`);
      // lead/collab of the stored ASSIGNED_TO edges, as displayed
      const lead = a.assigned_to.filter((e: string[]) => e[0] === t.id && e[1] === 'lead').map((e: string[]) => orgLabel(e[2]));
      const collab = a.assigned_to.filter((e: string[]) => e[0] === t.id && e[1] === 'collab').map((e: string[]) => orgLabel(e[2]));
      expect(lead).toEqual([t.lead_org]);
      for (const c of collab) await expect(row).toContainText(c);
      await row.click();
      const dialog = rv.page.getByRole('dialog', { name: '업무 상세' });
      await expect(dialog).toContainText(t.id);
      await expect(dialog).toContainText(`주관: ${t.lead_org}`);
      const preds = a.precedes.filter((e: string[]) => e[1] === t.id).map((e: string[]) => e[0]);
      const succs = a.precedes.filter((e: string[]) => e[0] === t.id).map((e: string[]) => e[1]);
      const titleOf = (id: string) => apiTasks.find((x) => x.id === id)?.title as string;
      for (const p of preds) await expect(dialog).toContainText(titleOf(p));
      for (const s of succs) await expect(dialog).toContainText(titleOf(s));
      if (preds.length) { await expect(row).toContainText('막힘'); expect(t.status).toBe('막힘'); } // dependent task starts blocked
      await dialog.getByRole('button', { name: '닫기' }).click();
    }
    shown[a.request_id] = { tasks: apiTasks.map((t) => ({ id: t.id, title: t.title, status: t.status })), precedes: a.precedes };
  }
  await shot(rv.page, 'g05-tasks-auto-assigned');
  keep('g05_tasks_screen', shown);
});

test('G06 stored relationships (Cypher) == 업무 Topology screen == 업무 screen', async () => {
  const g = records().g06_graph;
  expect(g, 'g06_graph record').toBeTruthy();
  const rid = g.request_id as string;
  const cypher = new Set((g.cypher_edges as any[]).map((e) => e.join('|')));
  await rq.page.goto(`/observatory?request_id=${rid}`);
  await rq.page.getByRole('button', { name: '업무 Topology' }).click();
  await expect(rq.page.locator('.obs-topology article').first()).toBeVisible({ timeout: 30_000 });
  const nodes = await rq.page.locator('.obs-topology article').evaluateAll((els) =>
    els.map((e) => ({ id: e.getAttribute('data-node-id'), type: e.getAttribute('data-node-type'), text: (e as HTMLElement).innerText })));
  const edges = await rq.page.locator('.obs-edges li').evaluateAll((els) =>
    els.map((e) => [e.getAttribute('data-edge-kind'), e.getAttribute('data-edge-from'), e.getAttribute('data-edge-to'), e.getAttribute('data-edge-role') || null]));
  // nodes: request + each task + each org, exactly the stored ones
  expect(nodes.filter((n) => n.type === 'request').map((n) => n.id)).toEqual([rid]);
  expect(nodes.filter((n) => n.type === 'task').map((n) => n.id).sort()).toEqual(g.task_nodes.map((t: any) => t.id).sort());
  expect(nodes.filter((n) => n.type === 'org').map((n) => n.id).sort()).toEqual([...g.org_nodes].sort());
  for (const t of g.task_nodes) expect(nodes.find((n) => n.id === t.id)!.text).toContain(t.title);
  for (const o of g.org_nodes) expect(nodes.find((n) => n.id === o)!.text).toContain(orgName(o));
  // relationships: the screen lists exactly the stored HAS_TASK / ASSIGNED_TO / PRECEDES edges
  const shownEdges = new Set(edges.map((e) => e.join('|')));
  expect([...shownEdges].sort()).toEqual([...cypher].sort());
  expect(edges.filter((e) => e[0] === 'PRECEDES').length).toBe(g.precedes_edges.length);
  await shot(rq.page, 'g06-topology-business');
  // same request on the 업무 screen: tasks and predecessors
  await rv.page.goto('/tasks');
  const shownTasks: Record<string, string> = {};
  for (const t of g.task_nodes) {
    const row = rv.page.locator('.task-list button', { hasText: t.id });
    await expect(row).toBeVisible();
    await expect(row).toContainText(t.title);
    await row.click();
    const dialog = rv.page.getByRole('dialog', { name: '업무 상세' });
    for (const [from, to, fromTitle, toTitle] of g.precedes_edges as string[][]) {
      if (to === t.id) await expect(dialog).toContainText(fromTitle);
      if (from === t.id) await expect(dialog).toContainText(toTitle);
    }
    shownTasks[t.id] = (await dialog.innerText()).replace(/\s+/g, ' ').slice(0, 200);
    await dialog.getByRole('button', { name: '닫기' }).click();
  }
  await shot(rv.page, 'g06-tasks-screen');
  keep('g06_graph_ui', { request_id: rid, nodes: nodes.map((n) => `${n.type}:${n.id}`), edges: [...shownEdges], tasks_screen: shownTasks });
});
