import { defineConfig } from '@playwright/test';

const isRemoteVerify =
  process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true';

export default defineConfig({
  testDir: '.',
  testMatch: [
    /(?:^|\/)events-loading\.spec\.ts$/,
    /(?:^|\/)tests\/local_root_main_site\.spec\.ts$/,
    /(?:^|\/)tests\/favcreators-guest-9000\.spec\.ts$/,
    /(?:^|\/)tests\/favcreators-admin-login\.spec\.ts$/,
    /(?:^|\/)tests\/verify_remote_site\.spec\.ts$/,
    /(?:^|\/)tests\/debug_nav_menu\.spec\.ts$/,
    /(?:^|\/)tests\/no_js_errors\.spec\.ts$/,
    /(?:^|\/)tests\/nav_2xko_after_favcreators\.spec\.ts$/,
    /(?:^|\/)tests\/inspect_quick_nav_order\.spec\.ts$/,
    /(?:^|\/)tests\/promo_banner_alignment\.spec\.ts$/,
    /(?:^|\/)tests\/favcreators-db-notes-remote\.spec\.ts$/,
    /(?:^|\/)tests\/favcreators-guest-notes-local\.spec\.ts$/,
    /(?:^|\/)tests\/favcreators-remote-notes\.spec\.ts$/,
    /(?:^|\/)tests\/signin_button_visible\.spec\.ts$/,
    /(?:^|\/)tests\/signin_flow_debug\.spec\.ts$/,
    /(?:^|\/)tests\/signin_login_box_location\.spec\.ts$/,
    /(?:^|\/)tests\/my_events_save_persisted\.spec\.ts$/,
    /(?:^|\/)tests\/tooltip_overlap\.spec\.ts$/,
    /(?:^|\/)tests\/tooltip_overlap_puppeteer\.spec\.ts$/,
    /(?:^|\/)tests\/movieshows_overlap\.spec\.ts$/,
    /(?:^|\/)tests\/live-status-ninja-test\.spec\.ts$/,
    /(?:^|\/)tests\/creator_updates\.spec\.ts$/,
    /(?:^|\/)tests\/streamer-updates-comprehensive\.spec\.ts$/,
    /(?:^|\/)tests\/streamer-updates-user-param\.spec\.ts$/,
    /(?:^|\/)tests\/thumbnail-proxy\.spec\.ts$/,
    /(?:^|\/)tests\/live-streams-realtime\.spec\.ts$/,
    /(?:^|\/)tests\/live-offline-removal\.spec\.ts$/,
    /(?:^|\/)tests\/streamer-last-seen-api\.spec\.ts$/,
    /(?:^|\/)tests\/mental-health-resources\.spec\.ts$/,
    /(?:^|\/)tests\/vr_quick_wins\.spec\.ts$/,
    /(?:^|\/)tests\/vr_quick_wins_phase2\.spec\.ts$/,
    /(?:^|\/)tests\/vr_creators_auth\.spec\.ts$/,
    /(?:^|\/)tests\/vr_area_guide\.spec\.ts$/,
  ],
  timeout: isRemoteVerify ? 90000 : 30000,
  retries: isRemoteVerify ? 1 : 0,
  webServer: isRemoteVerify
    ? undefined
    : {
        command: 'python tools/serve_local.py',
        url: 'http://localhost:5173/',
        reuseExistingServer: !process.env.CI,
        timeout: 30000,
      },
  use: {
    baseURL: isRemoteVerify
      ? process.env.VERIFY_REMOTE_URL || 'https://findtorontoevents.ca'
      : 'http://localhost:5173',
    headless: true,
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    video: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
});
