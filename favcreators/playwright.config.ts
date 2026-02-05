// Playwright config for running tests
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  timeout: 30000,
  retries: 0,
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:5173/favcreators/',
  //   reuseExistingServer: !process.env.CI,
  // },
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    video: 'off',
    screenshot: 'on-first-failure',
  },
});
