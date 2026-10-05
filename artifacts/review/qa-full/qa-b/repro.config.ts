import {defineConfig} from '../../../../frontend/node_modules/@playwright/test/index.mjs';
import base from './playwright.config';
export default defineConfig({...base,testDir:'./repro',timeout:120000,expect:{timeout:15000},outputDir:'./browser-results',use:{...base.use,trace:'off',baseURL:'http://127.0.0.1:8791'}});
