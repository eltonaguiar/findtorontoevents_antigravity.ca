import { defineConfig } from '@playwright/test';

// Live-site validation config — no local webServer needed.
export default defineConfig({
  testDir: './tests',
  testMatch: '**/audit_live_js_errors_spec.ts',
  timeout: 90000,
  retries: 0,
  workers: 2,
  use: {
    headless: true,
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'Desktop Chrome',
      use: {
        viewport: { width: 1920, height: 1080 },
      },
    },
  ],
});
