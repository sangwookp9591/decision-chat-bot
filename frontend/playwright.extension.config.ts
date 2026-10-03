import { defineConfig, devices } from '@playwright/test';

// T38 extension scenario browser checks (see e2e/extension/extension.spec.ts). Requires X38_* environment variables.
const port = Number(process.env.E2E_PORT || 5338);
export default defineConfig({
  testDir: './e2e/extension', testMatch: 'extension.spec.ts', fullyParallel: false, retries: 0, reporter: 'list', workers: 1,
  use: { baseURL: `http://127.0.0.1:${port}`, trace: 'retain-on-failure', ...devices['Desktop Chrome'] },
  webServer: { command: `npx vite --config vite.e2e.config.ts --host 127.0.0.1`, url: `http://127.0.0.1:${port}`, reuseExistingServer: false, timeout: 30_000,
    env: { E2E_PORT: String(port), E2E_API: process.env.E2E_API || 'http://127.0.0.1:8138' } },
});
