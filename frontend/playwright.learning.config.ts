import { defineConfig, devices } from '@playwright/test';

// Dedicated config: runs only the rule-learning E2E against its own API/tenant (see e2e/learning.spec.ts).
const port = Number(process.env.E2E_PORT || 5336);
export default defineConfig({
  testDir: './e2e', testMatch: 'learning.spec.ts', fullyParallel: false, retries: 0, reporter: 'list',
  use: { baseURL: `http://127.0.0.1:${port}`, trace: 'retain-on-failure', ...devices['Desktop Chrome'] },
  webServer: { command: `npx vite --config vite.e2e.config.ts --host 127.0.0.1`, url: `http://127.0.0.1:${port}`, reuseExistingServer: false, timeout: 30_000,
    env: { E2E_PORT: String(port), E2E_API: process.env.E2E_API || 'http://127.0.0.1:8000' } },
});
