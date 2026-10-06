import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { warmupClientFiles } from './vite.warmup';
export default defineConfig(({ mode }) => { const root = decodeURIComponent(new URL('../', import.meta.url).pathname); const { AI_NAME } = loadEnv(mode, root, ''); return { define: { __AI_NAME__: JSON.stringify(AI_NAME || 'Decision AI') }, plugins: [react()], root: decodeURIComponent(new URL('.', import.meta.url).pathname), server: { proxy: { '/api': 'http://localhost:8000' }, warmup: { clientFiles: warmupClientFiles } } }; });
