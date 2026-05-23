import { defineConfig } from '@playwright/test';

const isRemoteVerify =
  process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true';

// Standalone Playwright config used by the SS1 event-filter test suite.
// The repo's main playwright.config.ts walks the entire repo to enumerate
// tests; on this Windows machine some peer worktree caches under
// .worktrees/*/.pytest_cache have restricted permissions (EPERM) which
// crashes the test runner before it can even collect tests. Scoping test
// discovery to a single directory avoids that scan entirely.
export default defineConfig({
  testDir: 'tests/playwright',
  testMatch: /test_event_date_filters\.spec\.ts$/,
  timeout: isRemoteVerify ? 180_000 : 60_000,
  retries: isRemoteVerify ? 1 : 0,
  use: {
    baseURL: isRemoteVerify
      ? process.env.VERIFY_REMOTE_URL || 'https://findtorontoevents.ca'
      : 'http://localhost:5173',
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
