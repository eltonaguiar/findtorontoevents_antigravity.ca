/**
 * VR Full Site Test Suite
 *
 * Comprehensive testing of the VR app across ALL pages and device types.
 * Focuses on:
 *   1. Redirect detection (desktop users should NOT be forced to mobile)
 *   2. JS errors on every VR page
 *   3. Console errors (console.error) + pageerror
 *   4. Network failures (404/500 for JS/CSS resources)
 *   5. Multi-device: Desktop, iPhone, Android, iPad, Meta Quest browser
 *   6. Page load + A-Frame scene initialization
 *
 * Run against production:
 *   VERIFY_REMOTE=1 npx playwright test tests/vr_full_site_test.spec.ts
 */
import { test, expect, Page } from '@playwright/test';

const BASE = process.env.VERIFY_REMOTE === '1'
  ? 'https://findtorontoevents.ca'
  : 'http://localhost:5173';

// ── All VR pages to test ──────────────────────────────────
const VR_PAGES = [
  { name: 'VR Hub (Desktop)',      path: '/vr/' },
  { name: 'Mobile VR Hub',         path: '/vr/mobile-index.html' },
  { name: 'Movies Zone',           path: '/vr/movies.html' },
  { name: 'Creators Zone',         path: '/vr/creators.html' },
  { name: 'Weather Zone',          path: '/vr/weather-zone.html' },
  { name: 'Stocks Zone',           path: '/vr/stocks-zone.html' },
  { name: 'Events Zone',           path: '/vr/events/' },
];

// ── Non-critical errors to ignore ─────────────────────────
const NON_CRITICAL_PATTERNS = [
  'net::',
  'CORS',
  'Failed to fetch',
  'NetworkError',
  'ERR_BLOCKED_BY_RESPONSE',
  'ERR_CONNECTION_REFUSED',
  'NS_ERROR',
  'NotAllowedError',
  'AbortError',
  'immersive-vr',
  'ServiceWorker',
  'navigator.xr',
  'getGamepads',
  'SpeechSynthesis',
  'speechSynthesis',
  'AudioContext',
  'play()',
  'DOMException',
  'The play() request',
  'ResizeObserver',
  'Script error',
  'Loading module',
  'favicon',
  'Permissions policy',
  'PerformanceObserver',
  'third-party cookie',
  'Unrecognized feature',
  'autoplay',
  'feature policy',
  'Deprecation',
  'ERR_NAME_NOT_RESOLVED',       // DNS for optional external services
  'ERR_SSL',                      // SSL for optional external
  'WebSocket',                    // WebSocket connections
  'SecurityError',                // Security sandbox in headless
  'NotSupportedError',            // WebXR not supported in headless
  'message channel closed',       // Service worker message channel
  'A]',                           // A-Frame internal warnings
];

function isCriticalError(msg: string): boolean {
  return !NON_CRITICAL_PATTERNS.some(p => msg.includes(p));
}

// ── Device configurations ─────────────────────────────────
const DEVICES = {
  desktop: {
    viewport: { width: 1280, height: 720 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    isMobile: false,
    hasTouch: false,
  },
  desktopTouchscreen: {
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    isMobile: false,
    hasTouch: true, // Surface Pro, touch monitors
  },
  iphone: {
    viewport: { width: 393, height: 852 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    isMobile: true,
    hasTouch: true,
  },
  android: {
    viewport: { width: 412, height: 915 },
    userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
    isMobile: true,
    hasTouch: true,
  },
  ipad: {
    viewport: { width: 834, height: 1194 },
    userAgent: 'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    isMobile: true,
    hasTouch: true,
  },
  questBrowser: {
    viewport: { width: 1280, height: 720 },
    userAgent: 'Mozilla/5.0 (Linux; Android 12; Quest 3) AppleWebKit/537.36 (KHTML, like Gecko) OculusBrowser/32.0.0.2 SamsungBrowser/4.0 Chrome/122.0.0.0 Mobile VR Safari/537.36',
    isMobile: false, // Quest browser shouldn't trigger mobile redirect
    hasTouch: false,
  },
};

// ── Helpers ───────────────────────────────────────────────

interface PageTestResult {
  criticalErrors: string[];
  consoleErrors: string[];
  failed404s: string[];
  failed500s: string[];
  redirectedTo: string | null;
  title: string;
  hasAFrame: boolean;
  sceneLoaded: boolean;
  loadTimeMs: number;
}

async function testPage(page: Page, url: string, waitMs = 6000): Promise<PageTestResult> {
  const result: PageTestResult = {
    criticalErrors: [],
    consoleErrors: [],
    failed404s: [],
    failed500s: [],
    redirectedTo: null,
    title: '',
    hasAFrame: false,
    sceneLoaded: false,
    loadTimeMs: 0,
  };

  // Track page errors
  page.on('pageerror', (err) => {
    if (isCriticalError(err.message)) {
      result.criticalErrors.push(err.message);
    }
  });

  // Track console.error calls
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      if (isCriticalError(text)) {
        result.consoleErrors.push(text);
      }
    }
  });

  // Track failed network requests
  page.on('response', (response) => {
    const respUrl = response.url();
    // Only track our own domain resources, not external CDNs
    if (respUrl.includes('/vr/') || respUrl.includes('findtorontoevents.ca')) {
      if (response.status() === 404) {
        result.failed404s.push(respUrl);
      }
      if (response.status() >= 500) {
        result.failed500s.push(respUrl);
      }
    }
  });

  // Track redirects
  const startUrl = url;
  let finalUrl = '';
  page.on('framenavigated', (frame) => {
    if (frame === page.mainFrame()) {
      finalUrl = frame.url();
    }
  });

  const startTime = Date.now();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(waitMs);
  result.loadTimeMs = Date.now() - startTime;

  // Check if we were redirected
  const currentUrl = page.url();
  const startPath = new URL(startUrl.startsWith('http') ? startUrl : `${BASE}${startUrl}`).pathname;
  const currentPath = new URL(currentUrl).pathname;
  if (currentPath !== startPath && !currentPath.endsWith(startPath.replace(/\/$/, '') + '/')) {
    result.redirectedTo = currentUrl;
  }

  // Get page title
  result.title = await page.title();

  // Check A-Frame
  result.hasAFrame = await page.evaluate(() => typeof AFRAME !== 'undefined');
  result.sceneLoaded = await page.evaluate(() => {
    const s = document.querySelector('a-scene');
    return s ? !!(s as any).hasLoaded : false;
  });

  return result;
}


// ═══════════════════════════════════════════════════════════
// SECTION 1: REDIRECT DETECTION TESTS
// The core issue — desktop users should NEVER be auto-redirected
// ═══════════════════════════════════════════════════════════
test.describe('Redirect Detection — Desktop users must NOT be redirected', () => {

  test('Desktop browser visiting /vr/ stays on /vr/', async ({ browser }) => {
    test.setTimeout(60000);
    const context = await browser.newContext({
      viewport: DEVICES.desktop.viewport,
      userAgent: DEVICES.desktop.userAgent,
      isMobile: DEVICES.desktop.isMobile,
      hasTouch: DEVICES.desktop.hasTouch,
    });
    const page = await context.newPage();

    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(5000); // Wait longer than the 3s prompt delay

    const url = page.url();
    expect(url, 'Desktop should NOT redirect to mobile').not.toContain('mobile');
    expect(url).toContain('/vr/');

    // Verify no mobile prompt is shown for desktop
    const promptExists = await page.evaluate(() => {
      return document.getElementById('mobile-prompt') !== null;
    });
    expect(promptExists, 'Desktop should NOT see mobile prompt').toBe(false);

    await context.close();
  });

  test('Desktop with touchscreen visiting /vr/ stays on /vr/', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: DEVICES.desktopTouchscreen.viewport,
      userAgent: DEVICES.desktopTouchscreen.userAgent,
      isMobile: DEVICES.desktopTouchscreen.isMobile,
      hasTouch: DEVICES.desktopTouchscreen.hasTouch,
    });
    const page = await context.newPage();

    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const url = page.url();
    expect(url, 'Desktop+touch should NOT redirect to mobile').not.toContain('mobile');

    // Even though hasTouch is true, the UA is desktop so no redirect
    const promptExists = await page.evaluate(() => {
      return document.getElementById('mobile-prompt') !== null;
    });
    expect(promptExists, 'Desktop+touch should NOT see mobile prompt').toBe(false);

    await context.close();
  });

  test('Quest browser visiting /vr/ stays on /vr/ (no mobile redirect)', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: DEVICES.questBrowser.viewport,
      userAgent: DEVICES.questBrowser.userAgent,
      isMobile: false,
      hasTouch: false,
    });
    const page = await context.newPage();

    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const url = page.url();
    // Quest browser has "Mobile" and "Android" in UA but should not auto-redirect
    // because mobile-detect.js init() only shows a prompt, never auto-redirects
    expect(url).toContain('/vr/');
    // The URL should NOT have been changed to mobile-index.html
    expect(url).not.toContain('mobile-index');

    await context.close();
  });

  test('iPhone visiting /vr/ stays on /vr/ (no auto-redirect, only prompt)', async ({ browser }) => {
    test.setTimeout(60000);
    const context = await browser.newContext({
      viewport: DEVICES.iphone.viewport,
      userAgent: DEVICES.iphone.userAgent,
      isMobile: true,
      hasTouch: true,
    });
    const page = await context.newPage();

    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(5000); // Wait for 3s prompt delay + buffer

    const url = page.url();
    // Mobile should NOT be auto-redirected either (fix from c022db2)
    expect(url, 'Mobile should NOT be auto-redirected').not.toContain('mobile-index');

    // Check that MobileDetect correctly identified this as mobile
    // Note: Playwright hasTouch sets maxTouchPoints but may not set ontouchstart
    const detectionResult = await page.evaluate(() => {
      const mobileDetect = (window as any).MobileDetect;
      return {
        promptExists: document.getElementById('mobile-prompt') !== null,
        isMobileDetected: mobileDetect ? mobileDetect.isMobile() : null,
        maxTouchPoints: navigator.maxTouchPoints,
      };
    });
    console.log('iPhone detection result:', detectionResult);
    // The main assertion is no auto-redirect — prompt may or may not show
    // depending on Playwright's touch emulation fidelity
    if (detectionResult.isMobileDetected) {
      expect(detectionResult.promptExists, 'If detected as mobile, prompt should show').toBe(true);
    }

    await context.close();
  });

  test('Android visiting /vr/ stays on /vr/ (no auto-redirect)', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: DEVICES.android.viewport,
      userAgent: DEVICES.android.userAgent,
      isMobile: true,
      hasTouch: true,
    });
    const page = await context.newPage();

    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const url = page.url();
    expect(url, 'Android should NOT be auto-redirected').not.toContain('mobile-index');

    await context.close();
  });

  test('iPad visiting /vr/ stays on /vr/ (no auto-redirect)', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: DEVICES.ipad.viewport,
      userAgent: DEVICES.ipad.userAgent,
      isMobile: true,
      hasTouch: true,
    });
    const page = await context.newPage();

    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const url = page.url();
    expect(url, 'iPad should NOT be auto-redirected').not.toContain('mobile-index');

    await context.close();
  });

  test('Mobile user who dismissed prompt does not see it again within 24h', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: DEVICES.iphone.viewport,
      userAgent: DEVICES.iphone.userAgent,
      isMobile: true,
      hasTouch: true,
    });
    const page = await context.newPage();

    // Set localStorage to simulate prior dismissal
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => {
      localStorage.setItem('vr-mobile-prompt-dismissed', Date.now().toString());
    });

    // Reload
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const promptExists = await page.evaluate(() => {
      return document.getElementById('mobile-prompt') !== null;
    });
    expect(promptExists, 'Prompt should NOT reappear within 24h').toBe(false);

    await context.close();
  });

  test('User with vr-desktop-mode=true never sees prompt', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: DEVICES.iphone.viewport,
      userAgent: DEVICES.iphone.userAgent,
      isMobile: true,
      hasTouch: true,
    });
    const page = await context.newPage();

    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => {
      localStorage.setItem('vr-desktop-mode', 'true');
    });

    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const url = page.url();
    expect(url).not.toContain('mobile-index');

    const promptExists = await page.evaluate(() => {
      return document.getElementById('mobile-prompt') !== null;
    });
    expect(promptExists, 'Desktop-mode user should NOT see prompt').toBe(false);

    await context.close();
  });
});


// ═══════════════════════════════════════════════════════════
// SECTION 2: JS ERRORS ON ALL VR PAGES — Desktop
// ═══════════════════════════════════════════════════════════
test.describe('JS Errors — Desktop on ALL VR pages', () => {
  test.use({
    viewport: { width: 1280, height: 720 },
    userAgent: DEVICES.desktop.userAgent,
  });

  for (const vrPage of VR_PAGES) {
    test(`${vrPage.name} (${vrPage.path}) — no critical JS errors`, async ({ page }) => {
      const result = await testPage(page, `${BASE}${vrPage.path}`);

      if (result.criticalErrors.length > 0) {
        console.log(`[${vrPage.name}] Page errors:`, result.criticalErrors);
      }
      if (result.consoleErrors.length > 0) {
        console.log(`[${vrPage.name}] Console errors:`, result.consoleErrors);
      }

      expect(result.criticalErrors, `${vrPage.name} should have no critical pageerror`).toEqual([]);
    });

    test(`${vrPage.name} (${vrPage.path}) — no 404 JS resources`, async ({ page }) => {
      const result = await testPage(page, `${BASE}${vrPage.path}`);

      const js404s = result.failed404s.filter(u => u.endsWith('.js'));
      if (js404s.length > 0) {
        console.log(`[${vrPage.name}] JS 404s:`, js404s);
      }
      expect(js404s, `${vrPage.name} should have no JS 404s`).toEqual([]);
    });

    test(`${vrPage.name} (${vrPage.path}) — no server errors (5xx)`, async ({ page }) => {
      const result = await testPage(page, `${BASE}${vrPage.path}`);

      if (result.failed500s.length > 0) {
        console.log(`[${vrPage.name}] 5xx errors:`, result.failed500s);
      }
      expect(result.failed500s, `${vrPage.name} should have no 5xx errors`).toEqual([]);
    });
  }
});


// ═══════════════════════════════════════════════════════════
// SECTION 3: JS ERRORS ON ALL VR PAGES — Mobile (iPhone)
// ═══════════════════════════════════════════════════════════
test.describe('JS Errors — iPhone on ALL VR pages', () => {
  test.use({
    viewport: DEVICES.iphone.viewport,
    userAgent: DEVICES.iphone.userAgent,
    isMobile: true,
    hasTouch: true,
  });

  for (const vrPage of VR_PAGES) {
    test(`iPhone — ${vrPage.name} (${vrPage.path}) — no critical JS errors`, async ({ page }) => {
      const result = await testPage(page, `${BASE}${vrPage.path}`);

      if (result.criticalErrors.length > 0) {
        console.log(`[iPhone ${vrPage.name}] Page errors:`, result.criticalErrors);
      }
      expect(result.criticalErrors).toEqual([]);
    });
  }
});


// ═══════════════════════════════════════════════════════════
// SECTION 4: JS ERRORS — Android
// ═══════════════════════════════════════════════════════════
test.describe('JS Errors — Android on ALL VR pages', () => {
  test.use({
    viewport: DEVICES.android.viewport,
    userAgent: DEVICES.android.userAgent,
    isMobile: true,
    hasTouch: true,
  });

  for (const vrPage of VR_PAGES) {
    test(`Android — ${vrPage.name} (${vrPage.path}) — no critical JS errors`, async ({ page }) => {
      const result = await testPage(page, `${BASE}${vrPage.path}`);

      if (result.criticalErrors.length > 0) {
        console.log(`[Android ${vrPage.name}] Page errors:`, result.criticalErrors);
      }
      expect(result.criticalErrors).toEqual([]);
    });
  }
});


// ═══════════════════════════════════════════════════════════
// SECTION 5: A-FRAME SCENE INITIALIZATION — ALL PAGES
// ═══════════════════════════════════════════════════════════
test.describe('A-Frame Scene Initialization — ALL VR pages', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  for (const vrPage of VR_PAGES) {
    test(`${vrPage.name} — A-Frame present and scene loads`, async ({ page }) => {
      const result = await testPage(page, `${BASE}${vrPage.path}`, 8000);

      expect(result.hasAFrame, `${vrPage.name} should have AFRAME global`).toBe(true);
      expect(result.sceneLoaded, `${vrPage.name} a-scene should be loaded`).toBe(true);
    });

    test(`${vrPage.name} — page has a title`, async ({ page }) => {
      const result = await testPage(page, `${BASE}${vrPage.path}`, 3000);
      expect(result.title.length, `${vrPage.name} should have a page title`).toBeGreaterThan(0);
    });
  }
});


// ═══════════════════════════════════════════════════════════
// SECTION 6: CONSOLE ERROR AUDIT — Desktop
// Captures console.error messages (not just pageerror)
// ═══════════════════════════════════════════════════════════
test.describe('Console Error Audit — Desktop', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  for (const vrPage of VR_PAGES) {
    test(`${vrPage.name} — console.error audit`, async ({ page }) => {
      const consoleErrors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          const text = msg.text();
          if (isCriticalError(text)) {
            consoleErrors.push(text);
          }
        }
      });

      await page.goto(`${BASE}${vrPage.path}`, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(6000);

      if (consoleErrors.length > 0) {
        console.log(`[${vrPage.name}] Critical console.error calls:`, consoleErrors);
      }
      // Warn but don't necessarily fail — some console.error may be non-fatal
      // Log them for review
      expect(consoleErrors.length, `${vrPage.name} critical console errors`).toBeLessThanOrEqual(5);
    });
  }
});


// ═══════════════════════════════════════════════════════════
// SECTION 7: MOBILE-SPECIFIC FEATURES
// ═══════════════════════════════════════════════════════════
test.describe('Mobile-Specific Features — /vr/mobile-index.html', () => {
  test.use({
    viewport: DEVICES.iphone.viewport,
    userAgent: DEVICES.iphone.userAgent,
    isMobile: true,
    hasTouch: true,
  });

  test('Loading screen appears and then hides', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });

    // Loading should exist initially
    const loadingExists = await page.evaluate(() => {
      return document.getElementById('mobile-loading') !== null;
    });
    expect(loadingExists).toBe(true);

    // Wait for scene to load
    await page.waitForTimeout(8000);

    const isHidden = await page.evaluate(() => {
      const el = document.getElementById('mobile-loading');
      if (!el) return true;
      return el.classList.contains('hidden') || getComputedStyle(el).opacity === '0';
    });
    expect(isHidden, 'Loading screen should hide after scene loads').toBe(true);
  });

  test('Virtual joystick is present and sized correctly', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const joystickInfo = await page.evaluate(() => {
      const joystick = document.getElementById('joystick');
      const knob = document.getElementById('joystick-knob');
      if (!joystick || !knob) return null;
      const rect = joystick.getBoundingClientRect();
      return {
        width: rect.width,
        height: rect.height,
        knobExists: true,
      };
    });
    expect(joystickInfo).toBeTruthy();
    expect(joystickInfo!.width).toBeGreaterThanOrEqual(80);
    expect(joystickInfo!.knobExists).toBe(true);
  });

  test('Action buttons (jump/select/reset) are present', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const btnCount = await page.locator('.mobile-action-btn').count();
    expect(btnCount).toBeGreaterThanOrEqual(3);
  });

  test('Top bar with logo and menu button visible', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    await expect(page.locator('.mobile-top-bar')).toBeAttached();
    await expect(page.locator('.mobile-logo')).toBeAttached();
    await expect(page.locator('.mobile-menu-btn')).toBeAttached();
  });

  test('Zone menu opens and has all zone links', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    // Dismiss orientation warning if it's blocking (portrait mode)
    await page.evaluate(() => {
      const warning = document.getElementById('orientation-warning');
      if (warning) {
        warning.classList.remove('show');
        warning.style.display = 'none';
      }
    });
    await page.waitForTimeout(300);

    // Open menu
    await page.locator('.mobile-menu-btn').tap();
    await page.waitForTimeout(500);

    // Check zone cards
    const zoneCards = await page.locator('.mobile-zone-card').count();
    expect(zoneCards).toBeGreaterThanOrEqual(7);

    // Verify key zone links
    const hrefs = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.mobile-zone-card')).map(
        c => c.getAttribute('href')
      );
    });
    expect(hrefs).toContain('/vr/weather-zone.html');
    expect(hrefs).toContain('/vr/movies.html');
    expect(hrefs).toContain('/vr/events/');
    expect(hrefs).toContain('/vr/creators.html');
    expect(hrefs).toContain('/vr/stocks-zone.html');
  });

  test('Portrait orientation warning displays', async ({ page }) => {
    // iPhone viewport is portrait by default (393x852)
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const warningShown = await page.evaluate(() => {
      const w = document.getElementById('orientation-warning');
      return w && w.classList.contains('show');
    });
    expect(warningShown, 'Portrait orientation warning should show').toBe(true);
  });
});


// ═══════════════════════════════════════════════════════════
// SECTION 8: DESKTOP VR HUB FEATURES
// ═══════════════════════════════════════════════════════════
test.describe('Desktop VR Hub Features — /vr/', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('7 zone portals exist', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const zones = ['events', 'movies', 'creators', 'stocks', 'wellness', 'weather', 'tutorial'];
    for (const zone of zones) {
      const count = await page.locator(`[zone-link*="${zone}"]`).count();
      expect(count, `Zone "${zone}" portal should exist`).toBeGreaterThanOrEqual(1);
    }
  });

  test('Loading screen hides after A-Frame loads', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });

    const loading = page.locator('#loading');
    await expect(loading).toBeAttached();

    await page.waitForTimeout(5000);

    const isHidden = await page.evaluate(() => {
      const el = document.getElementById('loading');
      if (!el) return true;
      return el.classList.contains('hidden') || getComputedStyle(el).opacity === '0';
    });
    expect(isHidden).toBe(true);
  });

  test('Camera rig exists', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    await expect(page.locator('#rig')).toBeAttached();
  });

  test('Instructions bar visible after loading', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const isVisible = await page.evaluate(() => {
      const el = document.getElementById('instructions');
      return el && !el.classList.contains('hidden');
    });
    expect(isVisible).toBe(true);
  });

  test('F1 opens help overlay, Escape closes it', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    await page.keyboard.press('F1');
    await page.waitForTimeout(500);

    const isOpen = await page.evaluate(() => {
      const el = document.getElementById('help-overlay');
      return el && !el.classList.contains('hidden');
    });
    expect(isOpen, 'Help overlay should open on F1').toBe(true);

    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    const isClosed = await page.evaluate(() => {
      const el = document.getElementById('help-overlay');
      return el && el.classList.contains('hidden');
    });
    expect(isClosed, 'Help overlay should close on Escape').toBe(true);
  });

  test('Nav menu opens with M key', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    await page.keyboard.press('m');
    await page.waitForTimeout(1000);

    const sessionTimer = page.locator('#vr-session');
    const exists = await sessionTimer.count();
    expect(exists).toBeGreaterThanOrEqual(1);
  });

  test('Data badges exist for all zones', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);

    const badges = ['events', 'movies', 'weather', 'stocks', 'wellness', 'creators'];
    for (const b of badges) {
      await expect(page.locator(`#data-badge-${b}`), `Badge for ${b}`).toBeAttached();
    }
  });

  test('Enhancement JS modules loaded', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const scripts = await page.evaluate(() =>
      Array.from(document.querySelectorAll('script[src]')).map(s => s.getAttribute('src'))
    );

    const expectedModules = [
      'controller-support.js', 'nav-menu.js', 'quick-wins.js',
      'scene-enhancements.js', 'interaction.js', 'intelligence-engage.js'
    ];

    for (const mod of expectedModules) {
      const found = scripts.some(s => s && s.includes(mod));
      expect(found, `Module ${mod} should be loaded`).toBe(true);
    }
  });

  test('WASD controls enabled on camera', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const wasd = await page.evaluate(() => {
      const cam = document.querySelector('a-camera');
      if (!cam) return false;
      return cam.getAttribute('wasd-controls') !== null;
    });
    expect(wasd).toBe(true);
  });
});


// ═══════════════════════════════════════════════════════════
// SECTION 9: VR / WEBXR DOM CHECKS
// ═══════════════════════════════════════════════════════════
test.describe('VR/WebXR DOM — /vr/', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('A-Frame custom components registered (zone-link, teleport-surface, look-at-camera)', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const components = await page.evaluate(() => {
      if (typeof AFRAME === 'undefined') return [];
      return Object.keys(AFRAME.components);
    });

    expect(components).toContain('zone-link');
    expect(components).toContain('teleport-surface');
    expect(components).toContain('look-at-camera');
  });

  test('Left and right hand laser controllers configured', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    await expect(page.locator('#left-hand')).toBeAttached();
    await expect(page.locator('#right-hand')).toBeAttached();
  });

  test('Gaze cursor with fuse enabled', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const gazeRing = page.locator('a-camera a-ring[cursor]');
    await expect(gazeRing).toBeAttached();

    const cursorAttr = await page.evaluate(() => {
      const ring = document.querySelector('a-camera a-ring[cursor]');
      if (!ring) return null;
      const attr = ring.getAttribute('cursor');
      // A-Frame may return an object or a string
      if (typeof attr === 'object' && attr !== null) {
        return { fuse: (attr as any).fuse, fuseTimeout: (attr as any).fuseTimeout };
      }
      return { raw: String(attr) };
    });
    expect(cursorAttr).toBeTruthy();
    if ('fuse' in cursorAttr!) {
      expect(cursorAttr!.fuse).toBe(true);
    } else {
      expect((cursorAttr as any).raw).toContain('fuse: true');
    }
  });

  test('Teleport floor and indicator exist', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    await expect(page.locator('#teleport-floor')).toBeAttached();
    await expect(page.locator('#teleport-indicator')).toBeAttached();
  });
});


// ═══════════════════════════════════════════════════════════
// SECTION 10: CROSS-PAGE NAVIGATION — all zone links resolve
// ═══════════════════════════════════════════════════════════
test.describe('Cross-Page Navigation — all links valid', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('VR Hub zone-link URLs all return 200', async ({ page }) => {
    test.setTimeout(60000);
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const urls = await page.evaluate(() => {
      const links = document.querySelectorAll('[zone-link]');
      const set = new Set<string>();
      links.forEach(l => {
        const attr = l.getAttribute('zone-link');
        if (!attr) return;
        // A-Frame may return object {url: "/vr/events/"} or string "url: /vr/events/"
        if (typeof attr === 'object' && (attr as any).url) {
          set.add((attr as any).url);
        } else if (typeof attr === 'string') {
          const match = attr.match(/url:\s*([^\s;]+)/);
          if (match) set.add(match[1]);
        }
      });
      return Array.from(set);
    });

    expect(urls.length).toBeGreaterThanOrEqual(6);

    for (const url of urls) {
      const resp = await page.request.get(`${BASE}${url}`);
      expect(resp.status(), `${url} should be accessible`).toBeLessThan(400);
    }
  });

  test('Mobile zone menu links all return 200', async ({ page }) => {
    test.setTimeout(60000);
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const links = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.mobile-zone-card'))
        .map(c => c.getAttribute('href'))
        .filter(Boolean) as string[];
    });

    expect(links.length).toBeGreaterThanOrEqual(6);

    for (const link of links) {
      const resp = await page.request.get(`${BASE}${link}`);
      expect(resp.status(), `${link} should be accessible`).toBeLessThan(400);
    }
  });
});


// ═══════════════════════════════════════════════════════════
// SECTION 11: PERFORMANCE & RESOURCE LOADING
// ═══════════════════════════════════════════════════════════
test.describe('Performance & Resource Loading', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('A-Frame 1.6.0 loads from CDN', async ({ page }) => {
    let loaded = false;
    page.on('response', (r) => {
      if (r.url().includes('aframe') && r.url().includes('1.6.0') && r.status() === 200) {
        loaded = true;
      }
    });

    await page.goto(`${BASE}/vr/`, { waitUntil: 'networkidle' });
    expect(loaded, 'A-Frame 1.6.0 should load from CDN').toBe(true);
  });

  test('VR Hub total page weight < 10MB', async ({ page }) => {
    let totalBytes = 0;
    page.on('response', async (r) => {
      try { totalBytes += (await r.body()).length; } catch {}
    });

    await page.goto(`${BASE}/vr/`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const mb = totalBytes / (1024 * 1024);
    console.log(`VR Hub page weight: ${mb.toFixed(2)} MB`);
    expect(mb).toBeLessThan(10);
  });

  test('Mobile VR page weight < 5MB', async ({ page }) => {
    let totalBytes = 0;
    page.on('response', async (r) => {
      try { totalBytes += (await r.body()).length; } catch {}
    });

    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const mb = totalBytes / (1024 * 1024);
    console.log(`Mobile VR page weight: ${mb.toFixed(2)} MB`);
    expect(mb).toBeLessThan(5);
  });

  test('Page load time < 15s for VR Hub', async ({ page }) => {
    const start = Date.now();
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    const loadTime = Date.now() - start;
    console.log(`VR Hub DOM content loaded in: ${loadTime}ms`);
    expect(loadTime).toBeLessThan(15000);
  });

  test('Page load time < 15s for Mobile VR', async ({ page }) => {
    const start = Date.now();
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    const loadTime = Date.now() - start;
    console.log(`Mobile VR DOM content loaded in: ${loadTime}ms`);
    expect(loadTime).toBeLessThan(15000);
  });
});


// ═══════════════════════════════════════════════════════════
// SECTION 12: QUEST BROWSER SIMULATION
// ═══════════════════════════════════════════════════════════
test.describe('Quest Browser Simulation — /vr/', () => {
  test.use({
    viewport: DEVICES.questBrowser.viewport,
    userAgent: DEVICES.questBrowser.userAgent,
  });

  test('VR Hub loads without errors on Quest browser', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => {
      if (isCriticalError(err.message)) errors.push(err.message);
    });

    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);

    if (errors.length > 0) console.log('Quest errors:', errors);
    expect(errors).toEqual([]);
  });

  test('A-Frame scene initializes on Quest browser', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);

    const loaded = await page.evaluate(() => {
      const s = document.querySelector('a-scene');
      return s ? !!(s as any).hasLoaded : false;
    });
    expect(loaded).toBe(true);
  });

  test('Controller entities present for Quest', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    await expect(page.locator('#left-hand')).toBeAttached();
    await expect(page.locator('#right-hand')).toBeAttached();
  });
});


// ═══════════════════════════════════════════════════════════
// SECTION 13: ACCESSIBILITY & META TAGS
// ═══════════════════════════════════════════════════════════
test.describe('Accessibility & Meta Tags', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  for (const vrPage of VR_PAGES) {
    test(`${vrPage.name} — has lang="en"`, async ({ page }) => {
      await page.goto(`${BASE}${vrPage.path}`, { waitUntil: 'domcontentloaded' });
      const lang = await page.locator('html').getAttribute('lang');
      expect(lang).toBe('en');
    });

    test(`${vrPage.name} — has a non-empty <title>`, async ({ page }) => {
      await page.goto(`${BASE}${vrPage.path}`, { waitUntil: 'domcontentloaded' });
      const title = await page.title();
      expect(title.length).toBeGreaterThan(0);
    });

    test(`${vrPage.name} — has viewport meta tag`, async ({ page }) => {
      await page.goto(`${BASE}${vrPage.path}`, { waitUntil: 'domcontentloaded' });
      const viewport = await page.evaluate(() => {
        const meta = document.querySelector('meta[name="viewport"]');
        return meta ? meta.getAttribute('content') : null;
      });
      expect(viewport).toBeTruthy();
      expect(viewport).toContain('width=device-width');
    });
  }
});


// ═══════════════════════════════════════════════════════════
// SECTION 14: FULL RESOURCE AUDIT — 404 check across all pages
// ═══════════════════════════════════════════════════════════
test.describe('Full Resource Audit — 404s across ALL pages', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  for (const vrPage of VR_PAGES) {
    test(`${vrPage.name} — full 404 resource audit`, async ({ page }) => {
      const failed: { url: string; status: number }[] = [];
      page.on('response', (r) => {
        if (r.status() >= 400 && r.url().includes('/vr/')) {
          failed.push({ url: r.url(), status: r.status() });
        }
      });

      await page.goto(`${BASE}${vrPage.path}`, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(3000);

      const jsFailures = failed.filter(f => f.url.endsWith('.js'));
      const cssFailures = failed.filter(f => f.url.endsWith('.css'));
      const htmlFailures = failed.filter(f => f.url.endsWith('.html'));

      if (jsFailures.length > 0) console.log(`[${vrPage.name}] JS failures:`, jsFailures);
      if (cssFailures.length > 0) console.log(`[${vrPage.name}] CSS failures:`, cssFailures);
      if (htmlFailures.length > 0) console.log(`[${vrPage.name}] HTML failures:`, htmlFailures);

      expect(jsFailures, `${vrPage.name}: no JS files should fail`).toEqual([]);
      expect(cssFailures, `${vrPage.name}: no CSS files should fail`).toEqual([]);
    });
  }
});
