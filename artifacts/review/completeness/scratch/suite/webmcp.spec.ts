import { expect, test } from '@playwright/test';

test('application remains usable with or without WebMCP support', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('body')).toBeVisible();
  const probe = await page.evaluate(async () => {
    const modelContext = (document as Document & { modelContext?: { getTools?: () => Promise<Array<{ name: string }>> } }).modelContext;
    if (!modelContext) return { supported: false, names: [] };
    const tools = await modelContext.getTools?.() || [];
    return { supported: true, names: tools.map((tool) => tool.name).filter((name) => ['search_requests', 'get_request', 'get_trace'].includes(name)) };
  });
  if (!probe.supported) expect(probe.names).toHaveLength(0);
  else expect(probe.names.sort()).toEqual(['get_request', 'get_trace', 'search_requests']);
});
