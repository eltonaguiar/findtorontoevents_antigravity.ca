import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '../tests',
  testMatch: /ms3_live_e2e\.spec\.ts$/,
  timeout: 120000,
  expect: { timeout: 15000 },
  use: {
    headless: true,
    ignoreHTTPSErrors: true,
  },
  projects: [
    {
      name: 'Desktop Chrome',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
