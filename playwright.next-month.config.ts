import { defineConfig } from '@playwright/test';

const isRemoteVerify =
  process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true';

export default defineConfig({
  testDir: 'tests',
  testMatch: ['events_next_month_filter.spec.ts'],
  timeout: 120_000,
  retries: 0,
  workers: 1,
  fullyParallel: false,
  use: {
    baseURL: isRemoteVerify
      ? process.env.VERIFY_REMOTE_URL || 'https://findtorontoevents.ca'
      : 'http://localhost:5173',
    headless: true,
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
    video: 'off',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'Desktop Chrome',
      use: {
        userAgent:
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      },
    },
  ],
});
