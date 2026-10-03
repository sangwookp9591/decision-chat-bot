// Dedicated config so E2E can run beside other dev servers: E2E_API / E2E_PORT select the backend and port.
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins: [react()], server: { port: Number(process.env.E2E_PORT || 5173), strictPort: true, proxy: { '/api': process.env.E2E_API || 'http://localhost:8000' } } });
