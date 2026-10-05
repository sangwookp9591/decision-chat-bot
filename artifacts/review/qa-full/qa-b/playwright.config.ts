import {defineConfig} from '../../../../frontend/node_modules/@playwright/test/index.mjs';
import base from '../../../../frontend/e2e/all.config';
export default defineConfig({...base,testDir:'../../../../frontend/e2e',projects:[{name:'chromium',use:{browserName:'chromium'}}],use:{...base.use,trace:'off',screenshot:'only-on-failure'},workers:1});
