// Playwright config for running tests
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  timeout: 30000,
  retries: 0,
  use: {
    headless: true,
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    video: 'off',
    screenshot: 'off',
  },
});
