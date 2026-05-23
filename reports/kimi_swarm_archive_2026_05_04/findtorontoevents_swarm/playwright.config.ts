/**
 * playwright.config.ts
 *
 * Comprehensive Playwright configuration for findtorontoevents.ca
 * Covers: Desktop Chrome, Desktop Firefox, Mobile Safari (iPhone 12)
 * Console error tracking, screenshot/video/trace on failure, CI vs local tuning.
 */

import { defineConfig, devices, PlaywrightTestConfig } from "@playwright/test";
import { createConsoleErrorTracker } from "./tests/console-error-utils";

/* ------------------------------------------------------------------ */
/*  Environment detection                                               */
/* ------------------------------------------------------------------ */

const IS_CI = !!process.env.CI;
const BASE_URL = process.env.BASE_URL || "https://findtorontoevents.ca";

/* ------------------------------------------------------------------ */
/*  Shared context fixture extension for console tracking               */
/* ------------------------------------------------------------------ */

declare module "@playwright/test" {
  interface Page {
    _consoleTracker?: ReturnType<typeof createConsoleErrorTracker>;
  }
}

/* ------------------------------------------------------------------ */
/*  Config                                                               */
/* ------------------------------------------------------------------ */

const config: PlaywrightTestConfig = {
  testDir: "./tests",

  /* ── Timeouts ── */
  timeout: 60000,
  expect: {
    timeout: 10000,
  },

  /* ── Parallelism ── */
  fullyParallel: true,
  workers: IS_CI ? 4 : undefined, // Local uses auto-detect

  /* ── Retries ── */
  retries: IS_CI ? 1 : 0,

  /* ── Reporters ── */
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "./playwright-report" }],
    ["json", { outputFile: "./playwright-report/test-results.json" }],
  ],

  /* ── Global setup / teardown ── */
  globalSetup: undefined,
  globalTeardown: undefined,

  /* ── Shared project settings ── */
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 15000,
    navigationTimeout: 30000,
    /* Collect browser console errors automatically via page events */
    launchOptions: {
      args: ["--disable-web-security"],
    },
  },

  /* ── Projects ── */
  projects: [
    {
      name: "Desktop Chrome",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 720 },
      },
    },
    {
      name: "Desktop Firefox",
      use: {
        ...devices["Desktop Firefox"],
        viewport: { width: 1280, height: 720 },
      },
    },
    {
      name: "Mobile Safari",
      use: {
        ...devices["iPhone 12"],
      },
    },
  ],

  /* ── WebServer (optional local dev) ── */
  webServer: undefined,
};

export default defineConfig(config);
