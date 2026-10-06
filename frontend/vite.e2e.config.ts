// Dedicated config so E2E can run beside other dev servers: E2E_API / E2E_PORT select the backend and port.
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { warmupClientFiles } from './vite.warmup';
export default defineConfig(({ mode }) => { const root = decodeURIComponent(new URL('../', import.meta.url).pathname); const { AI_NAME } = loadEnv(mode, root, ''); return {
  define: { __AI_NAME__: JSON.stringify(AI_NAME || 'Decision AI') },
  root: decodeURIComponent(new URL('.', import.meta.url).pathname),
  plugins: [react()],
  // VITE_CACHE_DIR gives scripts/measure-cold-start.mjs an empty dependency cache without touching the shared one.
  ...(process.env.VITE_CACHE_DIR ? { cacheDir: process.env.VITE_CACHE_DIR } : {}),
  server: { warmup: { clientFiles: warmupClientFiles }, port: Number(process.env.E2E_PORT || 5173), strictPort: true, proxy: { '/api': process.env.E2E_API || 'http://localhost:8000' } },
}; });
