import { defineConfig } from '@playwright/test';

// Standalone config for sports-betting day-filter test. Matches the same
// pattern as playwright.filters.config.ts to avoid the .worktrees/* EPERM
// crash that the main config triggers on Windows.
export default defineConfig({
  testDir: 'tests/playwright',
  testMatch: /test_sports_picks_day_filter\.spec\.ts$/,
  timeout: 120_000,
  retries: 0,
  use: {
    headless: true,
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'Desktop Chrome',
      use: {
        userAgent:
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 },
      },
    },
  ],
});
