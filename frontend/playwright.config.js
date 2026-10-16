import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./e2e',workers:1,timeout:30000,use:{baseURL:process.env.TEST_BASE_URL||'http://127.0.0.1:8000',
  channel:process.platform==='win32'?'msedge':undefined,headless:true,viewport:{width:1440,height:1100}},reporter:'list'});
