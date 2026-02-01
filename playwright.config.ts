import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: /events-loading\.spec\.ts/,
  timeout: 30000,
  retries: 0,
  use: {
    baseURL: 'http://127.0.0.1:9000',
    headless: true,
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    video: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
});
