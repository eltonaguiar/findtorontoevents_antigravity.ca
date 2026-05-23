import { defineConfig } from '@playwright/test';

// Temporary config for audit tests — sets testDir to tests/ to avoid
// EPERM on .pytest_cache at root level.
export default defineConfig({
  testDir: './tests',
  timeout: 60000,
  retries: 0,
  webServer: {
    command: 'python tools/serve_local.py',
    url: 'http://localhost:5173/',
    reuseExistingServer: true,
    timeout: 30000,
  },
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    video: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'Desktop Chrome',
      use: {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 },
      },
    },
  ],
});
