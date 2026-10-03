import { defineConfig, devices } from '@playwright/test';

// UX-2 source viewer + judgment map E2E: dedicated ports (API 8391, vite 5591), tenant t-ux2 (worker limited to it).
//   bash e2e/source-viewer/env.sh start && npx playwright test -c playwright.source-viewer.config.ts && bash e2e/source-viewer/env.sh stop
const port = Number(process.env.E2E_PORT || 5591);
export default defineConfig({
  testDir: './e2e/source-viewer', testMatch: '*.spec.ts', fullyParallel: false, workers: 1, retries: 0, reporter: 'list',
  outputDir: process.env.UX2_OUT || '../artifacts/ux2-e2e/results',
  use: { baseURL: `http://127.0.0.1:${port}`, trace: 'retain-on-failure', screenshot: 'only-on-failure', ...devices['Desktop Chrome'] },
  webServer: { command: 'npx vite --config vite.e2e.config.ts --host 127.0.0.1', url: `http://127.0.0.1:${port}`, reuseExistingServer: false, timeout: 30_000,
    env: { E2E_PORT: String(port), E2E_API: process.env.E2E_API || 'http://127.0.0.1:8391' } },
});
