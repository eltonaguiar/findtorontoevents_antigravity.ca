import { defineConfig } from '@playwright/test';

// Standalone config for the BESTIEJOB GitHub Pages artifact (docs/bestiejob).
// Serves the exact static output over http and exercises it in Chromium.
export default defineConfig({
  testDir: './tests',
  testMatch: /bestiejob-page\.spec\.ts$/,
  timeout: 30000,
  retries: 0,
  reporter: [['list']],
  // Set BESTIEJOB_URL to validate a deployed copy (e.g. the GitHub Pages URL)
  // instead of the local static server.
  webServer: process.env.BESTIEJOB_URL
    ? undefined
    : {
        command: 'python3 -m http.server 8099 --directory docs/bestiejob',
        url: 'http://127.0.0.1:8099/',
        reuseExistingServer: !process.env.CI,
        timeout: 30000,
      },
  use: {
    baseURL: process.env.BESTIEJOB_URL || 'http://127.0.0.1:8099',
    headless: true,
    viewport: { width: 1280, height: 800 },
    ignoreHTTPSErrors: true,
    screenshot: 'only-on-failure',
    launchOptions: {
      // Use an installed Chrome/Chromium instead of requiring a matching
      // Playwright browser download (cache revision can drift).
      executablePath:
        process.env.CHROME_PATH ||
        ['/usr/bin/google-chrome', '/usr/bin/chromium-browser', '/snap/bin/chromium']
          .find(p => { try { return require('fs').existsSync(p); } catch { return false; } }),
    },
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
