import { defineConfig, devices } from '@playwright/test';

// T21 acceptance UI scenarios: own vite port + API (E2E_API), dedicated tenant (E2E_TENANT, default t-acc21).
//   E2E_API=http://127.0.0.1:8121 E2E_PORT=5421 npx playwright test -c playwright.acceptance.config.ts
const port = Number(process.env.E2E_PORT || 5421);
export default defineConfig({
  testDir: './e2e/acceptance', fullyParallel: false, workers: 1, retries: 0, reporter: [['list'], ['json', { outputFile: process.env.ACC_UI_JSON || 'test-results/acceptance-ui.json' }]],
  use: { baseURL: `http://127.0.0.1:${port}`, trace: 'retain-on-failure', ...devices['Desktop Chrome'] },
  webServer: { command: 'npx vite --config vite.e2e.config.ts --host 127.0.0.1', url: `http://127.0.0.1:${port}`, reuseExistingServer: false, timeout: 30_000,
    env: { E2E_PORT: String(port), E2E_API: process.env.E2E_API || 'http://127.0.0.1:8121' } },
});
