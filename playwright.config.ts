import { defineConfig } from '@playwright/test';

const isRemoteVerify =
  process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true';

export default defineConfig({
  testDir: '.',
  testMatch: [
    /(?:^|\/)events-loading\.spec\.ts$/,
    /(?:^|\/)tests\/favcreators-guest-9000\.spec\.ts$/,
    /(?:^|\/)tests\/favcreators-admin-login\.spec\.ts$/,
    /(?:^|\/)tests\/verify_remote_site\.spec\.ts$/,
    /(?:^|\/)tests\/debug_nav_menu\.spec\.ts$/,
    /(?:^|\/)tests\/no_js_errors\.spec\.ts$/,
  ],
  timeout: isRemoteVerify ? 60000 : 30000,
  retries: 0,
  webServer: isRemoteVerify
    ? undefined
    : {
        command: 'python tools/serve_local.py',
        url: 'http://localhost:9000/',
        reuseExistingServer: !process.env.CI,
        timeout: 30000,
      },
  use: {
    baseURL: isRemoteVerify
      ? process.env.VERIFY_REMOTE_URL || 'https://findtorontoevents.ca'
      : 'http://localhost:9000',
    headless: true,
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    video: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
});
