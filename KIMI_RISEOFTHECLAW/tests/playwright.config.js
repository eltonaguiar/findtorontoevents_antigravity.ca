const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: '.',
  testMatch: 'mode-switching.spec.js',
  timeout: 60000,
  retries: 0,
  use: {
    baseURL: 'https://findtorontoevents.ca',
    headless: true,
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
  },
  reporter: [['list']],
});
