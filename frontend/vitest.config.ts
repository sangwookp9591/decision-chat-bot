import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig(({ mode }) => { const root = decodeURIComponent(new URL('../', import.meta.url).pathname); const { AI_NAME } = loadEnv(mode, root, ''); return { define: { __AI_NAME__: JSON.stringify(AI_NAME || 'Decision AI') }, plugins: [react()], test: { environment: 'jsdom', include: ['src/**/*.{test,spec}.{ts,tsx}'] } }; });
