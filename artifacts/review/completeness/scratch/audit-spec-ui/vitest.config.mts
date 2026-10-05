import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins: [react()], test: { environment: 'jsdom', include: ['../artifacts/review/completeness/scratch/audit-spec-ui/*.test.tsx'] } });
