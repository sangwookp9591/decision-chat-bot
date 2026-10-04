import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { warmupClientFiles } from './vite.warmup';
export default defineConfig({ plugins: [react()], server: { proxy: { '/api': 'http://localhost:8000' }, warmup: { clientFiles: warmupClientFiles } } });
