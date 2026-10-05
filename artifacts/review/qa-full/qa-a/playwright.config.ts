import {defineConfig} from '../../../../frontend/node_modules/@playwright/test';
import base from '../../../../frontend/e2e/all.config';
export default defineConfig({...base,testDir:'../../../..',testMatch:['frontend/e2e/**/*.spec.ts','artifacts/review/qa-full/qa-a/repro/*.spec.ts'],use:{...base.use,screenshot:'only-on-failure'},workers:1});
