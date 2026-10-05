import { defineConfig } from '@playwright/test';
import base from '../playwright.config';
export default defineConfig({ ...base, testDir: '.', use: { ...base.use, actionTimeout: 15_000 }, workers: 1 });
