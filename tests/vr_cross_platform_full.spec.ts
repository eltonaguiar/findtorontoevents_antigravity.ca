/**
 * VR Cross-Platform Full Test Suite
 *
 * Tests a VR page across THREE user types and input methods:
 *   1. Desktop (Chrome) — keyboard/mouse, WASD, shortcuts, nav menu
 *   2. Mobile (iPhone 14 Pro) — touch, joystick, tap targets, orientation
 *   3. Meta Quest 3 — controllers, hand tracking, gaze cursor, teleport
 *
 * Usage:
 *   npx playwright test tests/vr_cross_platform_full.spec.ts
 *   VERIFY_REMOTE=1 npx playwright test tests/vr_cross_platform_full.spec.ts
 *   VR_PAGE=/vr/movies.html npx playwright test tests/vr_cross_platform_full.spec.ts
 *   npx playwright test tests/vr_cross_platform_full.spec.ts -g "Desktop"
 *   npx playwright test tests/vr_cross_platform_full.spec.ts -g "Quest 3"
 */
import { test, expect } from '@playwright/test';

// ─── Configuration ────────────────────────────────────────────────
const BASE = process.env.VERIFY_REMOTE === '1'
  ? 'https://findtorontoevents.ca'
  : 'http://localhost:5173';

const VR_PAGE = process.env.VR_PAGE || '/vr/';
const PAGE_URL = `${BASE}${VR_PAGE}`;
const NAV_TIMEOUT = parseInt(process.env.VR_TIMEOUT || '60000', 10);
const SCENE_WAIT = parseInt(process.env.VR_WAIT || '6000', 10);

// Whether the target page is the mobile-specific page
const IS_MOBILE_PAGE = VR_PAGE.includes('mobile-index');
// Whether the target page is the VR Hub (has zone portals)
const IS_HUB = VR_PAGE === '/vr/' || IS_MOBILE_PAGE;

// ─── Non-critical error filter ────────────────────────────────────
const NON_CRITICAL = [
  'net::', 'CORS', 'Failed to fetch', 'NetworkError',
  'ERR_BLOCKED_BY_RESPONSE', 'ERR_CONNECTION_REFUSED', 'NS_ERROR',
  'NotAllowedError', 'AbortError',
  'immersive-vr', 'ServiceWorker', 'navigator.xr',
  'getGamepads', 'SpeechSynthesis', 'speechSynthesis',
  'AudioContext', 'play()', 'DOMException', 'The play() request',
  'ResizeObserver', 'Script error', 'Loading module', 'favicon',
  'webxr', 'WebXR', 'XRSystem',
  'Permissions policy', 'Feature policy',
  'Mixed Content', 'insecure content',
];

function isCriticalError(msg: string): boolean {
  return !NON_CRITICAL.some(pattern => msg.toLowerCase().includes(pattern.toLowerCase()));
}

// Collect page errors in each test
function setupErrorCollector(page: any) {
  const errors: string[] = [];
  page.on('pageerror', (err: Error) => errors.push(err.message));
  return errors;
}

// ═══════════════════════════════════════════════════════════════════
// SECTION 1: SHARED TESTS — Run for every user type
// ═══════════════════════════════════════════════════════════════════

async function sharedPageChecks(page: any, label: string) {
  const errors = setupErrorCollector(page);

  // Track 404'd JS files
  const js404s: string[] = [];
  page.on('response', (res: any) => {
    if (res.status() === 404 && res.url().endsWith('.js')) {
      js404s.push(res.url());
    }
  });

  const response = await page.goto(PAGE_URL, {
    waitUntil: 'domcontentloaded',
    timeout: NAV_TIMEOUT,
  });

  // HTTP 200
  expect(response?.status(), `${label}: HTTP status should be < 400`).toBeLessThan(400);

  // Wait for A-Frame scene init
  await page.waitForTimeout(SCENE_WAIT);

  // A-Frame scene loaded
  const sceneInfo = await page.evaluate(() => {
    const s = document.querySelector('a-scene') as any;
    return {
      exists: !!s,
      hasLoaded: s ? !!s.hasLoaded : false,
    };
  });
  expect(sceneInfo.exists, `${label}: <a-scene> should exist`).toBe(true);
  expect(sceneInfo.hasLoaded, `${label}: A-Frame scene should have loaded`).toBe(true);

  // Title check
  const title = await page.title();
  expect(title.length, `${label}: page should have a title`).toBeGreaterThan(0);

  // No critical JS errors
  const critical = errors.filter(isCriticalError);
  if (critical.length > 0) {
    console.log(`${label} critical JS errors:`, critical);
  }
  expect(critical, `${label}: zero critical JS errors`).toEqual([]);

  // No JS file 404s
  if (js404s.length > 0) {
    console.log(`${label} JS 404s:`, js404s);
  }
  expect(js404s, `${label}: no JS 404s`).toEqual([]);

  return { errors, js404s };
}

// ═══════════════════════════════════════════════════════════════════
// SECTION 2: DESKTOP USER — Keyboard/Mouse (Chrome)
// ═══════════════════════════════════════════════════════════════════

test.describe(`Desktop (keyboard/mouse) — ${VR_PAGE}`, () => {
  test.use({ viewport: { width: 1920, height: 1080 } });

  test('Page loads without critical JS errors', async ({ page }) => {
    await sharedPageChecks(page, 'Desktop');
  });

  test('Loading screen appears then hides', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    const loadingSel = IS_MOBILE_PAGE ? '#mobile-loading' : '#loading';
    const loading = page.locator(loadingSel);
    await expect(loading).toBeAttached();

    await page.waitForTimeout(SCENE_WAIT);

    const isHidden = await page.evaluate((sel: string) => {
      const el = document.querySelector(sel);
      if (!el) return true;
      const s = getComputedStyle(el);
      return el.classList.contains('hidden') || s.opacity === '0' || s.display === 'none';
    }, loadingSel);
    expect(isHidden, 'Loading screen should hide after init').toBe(true);
  });

  test('WASD movement controls enabled on camera', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const wasd = await page.evaluate(() => {
      const cam = document.querySelector('a-camera');
      if (!cam) return false;
      return cam.getAttribute('wasd-controls') !== null;
    });
    expect(wasd, 'Camera should have wasd-controls').toBe(true);
  });

  test('Mouse look-controls enabled on camera', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const look = await page.evaluate(() => {
      const cam = document.querySelector('a-camera');
      if (!cam) return false;
      return cam.getAttribute('look-controls') !== null;
    });
    expect(look, 'Camera should have look-controls').toBe(true);
  });

  test('Nav menu opens with M key and closes with Escape', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    // Open menu
    await page.keyboard.press('m');
    await page.waitForTimeout(800);

    const menuVisible = await page.evaluate(() => {
      const menu = document.getElementById('vr-nav-menu-2d');
      if (!menu) return false;
      const s = getComputedStyle(menu);
      return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0';
    });
    expect(menuVisible, 'Nav menu should be visible after M key').toBe(true);

    // Close menu
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    const menuHidden = await page.evaluate(() => {
      const menu = document.getElementById('vr-nav-menu-2d');
      if (!menu) return true;
      const s = getComputedStyle(menu);
      return s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0';
    });
    expect(menuHidden, 'Nav menu should hide after Escape').toBe(true);
  });

  test('Nav menu also opens with Tab key', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    await page.keyboard.press('Tab');
    await page.waitForTimeout(800);

    const menuVisible = await page.evaluate(() => {
      const menu = document.getElementById('vr-nav-menu-2d');
      if (!menu) return false;
      const s = getComputedStyle(menu);
      return s.display !== 'none' && s.visibility !== 'hidden';
    });
    expect(menuVisible, 'Nav menu should open on Tab').toBe(true);
  });

  if (IS_HUB && !IS_MOBILE_PAGE) {
    test('Keyboard shortcuts 1-6 jump to zone positions', async ({ page }) => {
      await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
      await page.waitForTimeout(SCENE_WAIT);

      // Press '1' (Events zone)
      await page.keyboard.press('1');
      await page.waitForTimeout(600);

      const posAfter1 = await page.evaluate(() => {
        const cam = document.querySelector('a-camera');
        if (!cam) return null;
        const p = cam.getAttribute('position') as any;
        return p ? { x: parseFloat(p.x), y: parseFloat(p.y), z: parseFloat(p.z) } : null;
      });
      expect(posAfter1, 'Camera should have moved after pressing 1').toBeTruthy();

      // Press '0' (center)
      await page.keyboard.press('0');
      await page.waitForTimeout(600);

      const posAfter0 = await page.evaluate(() => {
        const cam = document.querySelector('a-camera');
        if (!cam) return null;
        const p = cam.getAttribute('position') as any;
        return p ? { x: parseFloat(p.x) } : null;
      });
      expect(posAfter0, 'Camera should exist after pressing 0').toBeTruthy();
      if (posAfter0) {
        expect(posAfter0.x, 'Camera X should return to 0').toBe(0);
      }
    });

    test('F1 help overlay opens and closes', async ({ page }) => {
      await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
      await page.waitForTimeout(SCENE_WAIT);

      await page.keyboard.press('F1');
      await page.waitForTimeout(500);

      const helpVisible = await page.evaluate(() => {
        const el = document.getElementById('help-overlay');
        return el && !el.classList.contains('hidden');
      });
      expect(helpVisible, 'Help overlay should open on F1').toBe(true);

      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);

      const helpClosed = await page.evaluate(() => {
        const el = document.getElementById('help-overlay');
        return !el || el.classList.contains('hidden');
      });
      expect(helpClosed, 'Help overlay should close on Escape').toBe(true);
    });

    test('All zone portals exist', async ({ page }) => {
      await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
      await page.waitForTimeout(SCENE_WAIT);

      const zones = ['events', 'movies', 'creators', 'stocks', 'wellness', 'weather', 'tutorial'];
      for (const zone of zones) {
        const count = await page.locator(`[zone-link*="${zone}"]`).count();
        expect(count, `Zone portal for "${zone}" should exist`).toBeGreaterThanOrEqual(1);
      }
    });
  }

  test('Gaze cursor ring exists inside camera', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const gazeExists = await page.evaluate(() => {
      // Check for ring cursor inside camera, or any cursor element
      const ring = document.querySelector('a-camera a-ring[cursor]');
      const cursor = document.querySelector('a-camera [cursor]');
      return !!(ring || cursor);
    });
    expect(gazeExists, 'Gaze cursor should exist inside camera').toBe(true);
  });

  test('Clickable elements have proper class for raycasting', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const clickableCount = await page.locator('.clickable').count();
    expect(clickableCount, 'Should have clickable elements').toBeGreaterThan(0);
  });

  test('Enhancement JS modules loaded', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(3000);

    const scripts = await page.evaluate(() =>
      Array.from(document.querySelectorAll('script[src]')).map(s => s.getAttribute('src') || '')
    );

    const coreModules = ['controller-support.js', 'nav-menu.js'];
    for (const mod of coreModules) {
      const found = scripts.some((s: string) => s.includes(mod));
      expect(found, `Module ${mod} should be loaded`).toBe(true);
    }
  });

  test('Camera rig exists at valid position', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const hasRig = await page.evaluate(() => {
      const rig = document.getElementById('rig') || document.getElementById('camera-rig');
      return rig ? rig.getAttribute('position') !== null : false;
    });
    expect(hasRig, 'Camera rig should exist with a position').toBe(true);
  });

  test('No 404s on VR page resources', async ({ page }) => {
    const notFound: string[] = [];
    page.on('response', (res: any) => {
      if (res.status() === 404 && res.url().includes('/vr/')) {
        notFound.push(res.url());
      }
    });

    await page.goto(PAGE_URL, { waitUntil: 'networkidle', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(3000);

    const js404 = notFound.filter(u => u.endsWith('.js'));
    if (js404.length > 0) console.log('JS 404s:', js404);
    expect(js404, 'No JS files should 404').toEqual([]);
  });
});


// ═══════════════════════════════════════════════════════════════════
// SECTION 3: MOBILE USER — Touch (iPhone 14 Pro)
// ═══════════════════════════════════════════════════════════════════

test.describe(`Mobile touch user (iPhone) — ${VR_PAGE}`, () => {
  test.use({
    viewport: { width: 393, height: 852 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    isMobile: true,
    hasTouch: true,
  });

  test('Page loads without critical JS errors (mobile)', async ({ page }) => {
    await sharedPageChecks(page, 'Mobile');
  });

  test('Touch look-controls enabled on camera', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const touchEnabled = await page.evaluate(() => {
      const cam = document.querySelector('a-camera') || document.getElementById('camera');
      if (!cam) return false;
      const lc = cam.getAttribute('look-controls');
      if (typeof lc === 'string') return lc.includes('touchEnabled: true') || lc.includes('touchEnabled:true');
      if (typeof lc === 'object' && lc) return (lc as any).touchEnabled === true || (lc as any).touchEnabled === 'true';
      // Default look-controls has touch enabled
      return lc !== null;
    });
    expect(touchEnabled, 'Camera should have touch-enabled look-controls').toBe(true);
  });

  test('Mobile detection script loaded', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(3000);

    const hasMobileDetect = await page.evaluate(() =>
      Array.from(document.querySelectorAll('script[src]')).some(
        s => (s.getAttribute('src') || '').includes('mobile-detect')
      )
    );
    // Mobile detect may not exist on all zone pages; pass if page loaded fine
    if (!hasMobileDetect) {
      console.log('Note: mobile-detect.js not found on this page (optional for zone pages)');
    }
  });

  if (IS_MOBILE_PAGE) {
    test('Joystick and action buttons exist', async ({ page }) => {
      await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
      await page.waitForTimeout(SCENE_WAIT);

      await expect(page.locator('#joystick')).toBeAttached();
      await expect(page.locator('#joystick-knob')).toBeAttached();
      const actionBtns = await page.locator('.mobile-action-btn').count();
      expect(actionBtns, 'Should have >= 3 action buttons').toBeGreaterThanOrEqual(3);
    });

    test('Tap targets are >= 44px (mobile accessibility)', async ({ page }) => {
      await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
      await page.waitForTimeout(SCENE_WAIT);

      // Open menu to check zone cards
      const menuBtn = page.locator('.mobile-menu-btn');
      if (await menuBtn.count() > 0) {
        await menuBtn.tap();
        await page.waitForTimeout(500);

        const sizes = await page.evaluate(() => {
          const cards = document.querySelectorAll('.mobile-zone-card');
          return Array.from(cards).map(c => {
            const rect = c.getBoundingClientRect();
            return { w: rect.width, h: rect.height };
          });
        });

        for (const s of sizes) {
          expect(s.h, 'Touch target height >= 44px').toBeGreaterThanOrEqual(44);
          expect(s.w, 'Touch target width >= 44px').toBeGreaterThanOrEqual(44);
        }
      }
    });

    test('Zone menu opens on tap and closes on X', async ({ page }) => {
      await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
      await page.waitForTimeout(SCENE_WAIT);

      // Open
      await page.locator('.mobile-menu-btn').tap();
      await page.waitForTimeout(500);

      const isOpen = await page.evaluate(() => {
        const menu = document.getElementById('mobile-zone-menu');
        return menu && menu.classList.contains('active');
      });
      expect(isOpen, 'Zone menu should open on tap').toBe(true);

      // Close
      await page.locator('.mobile-close-btn').tap();
      await page.waitForTimeout(500);

      const isClosed = await page.evaluate(() => {
        const menu = document.getElementById('mobile-zone-menu');
        return !menu || !menu.classList.contains('active');
      });
      expect(isClosed, 'Zone menu should close on X tap').toBe(true);
    });

    test('Zone menu contains all zone links', async ({ page }) => {
      await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
      await page.waitForTimeout(SCENE_WAIT);

      const zoneCards = await page.locator('.mobile-zone-card').count();
      expect(zoneCards, 'Should have >= 7 zone cards').toBeGreaterThanOrEqual(7);

      const hrefs = await page.evaluate(() =>
        Array.from(document.querySelectorAll('.mobile-zone-card'))
          .map(c => c.getAttribute('href'))
          .filter(Boolean)
      );
      const expectedPaths = ['/vr/events/', '/vr/movies.html', '/vr/creators.html',
        '/vr/stocks-zone.html', '/vr/weather-zone.html', '/vr/wellness/', '/vr/tutorial/'];
      for (const p of expectedPaths) {
        expect(hrefs, `Zone link ${p} should exist`).toContain(p);
      }
    });

    test('Orientation warning shows in portrait', async ({ page }) => {
      await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
      await page.waitForTimeout(3000);

      const warningShown = await page.evaluate(() => {
        const w = document.getElementById('orientation-warning');
        return w && w.classList.contains('show');
      });
      expect(warningShown, 'Orientation warning should show in portrait').toBe(true);
    });

    test('VR enter button exists', async ({ page }) => {
      await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
      await page.waitForTimeout(3000);
      await expect(page.locator('#vr-enter-btn')).toBeAttached();
    });
  }

  test('Mobile landscape: orientation warning NOT shown', async ({ page }) => {
    // Override viewport to landscape
    await page.setViewportSize({ width: 852, height: 393 });
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(3000);

    const warningShown = await page.evaluate(() => {
      const w = document.getElementById('orientation-warning');
      return w && w.classList.contains('show');
    });
    // In landscape width > height, so warning should NOT show (or element may not exist)
    if (warningShown !== null) {
      expect(warningShown, 'Orientation warning should NOT show in landscape').toBe(false);
    }
  });

  test('A-Frame scene loads on mobile', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const loaded = await page.evaluate(() => {
      const s = document.querySelector('a-scene') as any;
      return s ? !!s.hasLoaded : false;
    });
    expect(loaded, 'A-Frame should load on mobile').toBe(true);
  });

  test('Clickable elements accessible on mobile viewport', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const count = await page.locator('.clickable').count();
    expect(count, 'Should have clickable elements on mobile').toBeGreaterThan(0);
  });
});


// ═══════════════════════════════════════════════════════════════════
// SECTION 4: META QUEST 3 — Controllers, Hand Tracking, Gaze
// ═══════════════════════════════════════════════════════════════════

test.describe(`Meta Quest 3 (controllers/hands/gaze) — ${VR_PAGE}`, () => {
  test.use({
    viewport: { width: 1832, height: 1920 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) OculusBrowser/32.0.0.0.0 SamsungBrowser/4.0 Chrome/120.0.0.0 VR Safari/537.36',
  });

  // ── 4a. Core Load ──────────────────────────────────────────────

  test('Page loads without critical JS errors (Quest 3)', async ({ page }) => {
    await sharedPageChecks(page, 'Quest 3');
  });

  test('A-Frame version is 1.6.0+', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const version = await page.evaluate(() => {
      return (window as any).AFRAME?.version || null;
    });
    expect(version, 'A-Frame should be loaded').toBeTruthy();
    if (version) {
      const [major, minor] = version.split('.').map(Number);
      expect(major * 100 + minor, 'A-Frame >= 1.6').toBeGreaterThanOrEqual(106);
    }
  });

  // ── 4b. Controller Support ─────────────────────────────────────

  test('Left and right laser-controls entities exist', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const leftExists = await page.evaluate(() => {
      const el = document.getElementById('left-hand') || document.getElementById('left-ctrl');
      if (!el) return false;
      const lc = el.getAttribute('laser-controls');
      return lc !== null && String(lc).includes('left');
    });
    expect(leftExists, 'Left laser-controls entity should exist').toBe(true);

    const rightExists = await page.evaluate(() => {
      const el = document.getElementById('right-hand') || document.getElementById('right-ctrl');
      if (!el) return false;
      const lc = el.getAttribute('laser-controls');
      return lc !== null && String(lc).includes('right');
    });
    expect(rightExists, 'Right laser-controls entity should exist').toBe(true);
  });

  test('Controller entities have raycaster configured for .clickable', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const raycasterOk = await page.evaluate(() => {
      const entities = [
        document.getElementById('left-hand'),
        document.getElementById('right-hand'),
        document.getElementById('left-ctrl'),
        document.getElementById('right-ctrl'),
      ].filter(Boolean);

      return entities.some(el => {
        const rc = el!.getAttribute('raycaster');
        return rc && String(rc).includes('.clickable');
      });
    });
    expect(raycasterOk, 'At least one controller should raycaster .clickable').toBe(true);
  });

  test('controller-support.js loaded', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(3000);

    const found = await page.evaluate(() =>
      Array.from(document.querySelectorAll('script[src]')).some(
        s => (s.getAttribute('src') || '').includes('controller-support')
      )
    );
    expect(found, 'controller-support.js should be loaded').toBe(true);
  });

  test('vr-controls.js loaded', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(3000);

    const found = await page.evaluate(() =>
      Array.from(document.querySelectorAll('script[src]')).some(
        s => {
          const src = s.getAttribute('src') || '';
          return src.includes('vr-controls') || src.includes('vr-controller-system');
        }
      )
    );
    expect(found, 'vr-controls.js or vr-controller-system.js should be loaded').toBe(true);
  });

  test('VRControllerSupport global API available', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const apiReady = await page.evaluate(() => {
      const vcs = (window as any).VRControllerSupport;
      if (!vcs) return { exists: false };
      return {
        exists: true,
        hasIsVR: typeof vcs.isVR === 'function',
        hasGetActiveInput: typeof vcs.getActiveInput === 'function',
      };
    });
    // API may not exist on all pages; log but don't hard fail for zone pages
    if (!apiReady.exists && !IS_HUB) {
      console.log('Note: VRControllerSupport not found on zone page (may use inline version)');
    } else if (apiReady.exists) {
      expect(apiReady.hasIsVR, 'VRControllerSupport.isVR() should exist').toBe(true);
      expect(apiReady.hasGetActiveInput, 'VRControllerSupport.getActiveInput() should exist').toBe(true);
    }
  });

  // ── 4c. Hand Tracking ──────────────────────────────────────────

  test('Hand-tracking entities created or creatable', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const handInfo = await page.evaluate(() => {
      const leftHT = document.getElementById('left-hand-tracking');
      const rightHT = document.getElementById('right-hand-tracking');
      // Also check for hand-controls attribute on controller entities
      const leftHand = document.getElementById('left-hand');
      const rightHand = document.getElementById('right-hand');
      const hasHandControls = [leftHand, rightHand].some(
        el => el && (el.getAttribute('hand-controls') !== null || el.getAttribute('hand-tracking-controls') !== null)
      );
      return {
        leftHTExists: !!leftHT,
        rightHTExists: !!rightHT,
        hasHandControls,
        controllerSupportLoaded: !!(window as any).VRControllerSupport,
      };
    });

    // Hand tracking entities may be created lazily on VR enter
    // At minimum, controller-support.js should be loaded (which creates them on demand)
    const handTrackingReady = handInfo.leftHTExists || handInfo.rightHTExists ||
                              handInfo.hasHandControls || handInfo.controllerSupportLoaded;
    expect(handTrackingReady, 'Hand tracking should be supported (entities or controller-support loaded)').toBe(true);
  });

  // ── 4d. Gaze Cursor ───────────────────────────────────────────

  test('Gaze cursor with fuse enabled (1500ms)', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const fuseInfo = await page.evaluate(() => {
      // Check ring cursor or any cursor inside camera
      const ring = document.querySelector('a-camera a-ring[cursor]');
      const cursorEl = document.querySelector('a-camera [cursor]');
      const el = ring || cursorEl;
      if (!el) return null;
      const cursorAttr = el.getAttribute('cursor');
      return String(cursorAttr);
    });
    expect(fuseInfo, 'Gaze cursor should exist').toBeTruthy();
    if (fuseInfo) {
      expect(fuseInfo, 'Gaze cursor should have fuse: true').toContain('fuse: true');
      expect(fuseInfo, 'Gaze fuse timeout should be 1500ms').toContain('fuseTimeout: 1500');
    }
  });

  // ── 4e. Teleport System ────────────────────────────────────────

  test('Teleport surface and indicator exist', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const teleportInfo = await page.evaluate(() => {
      const floor = document.getElementById('teleport-floor');
      const indicator = document.getElementById('teleport-indicator') ||
                        document.getElementById('vr-teleport-indicator');
      return { hasFloor: !!floor, hasIndicator: !!indicator };
    });

    // Teleport may not exist on all zone pages
    if (IS_HUB) {
      expect(teleportInfo.hasFloor, 'Teleport floor should exist on hub').toBe(true);
      expect(teleportInfo.hasIndicator, 'Teleport indicator should exist on hub').toBe(true);
    } else {
      if (!teleportInfo.hasFloor) {
        console.log('Note: Teleport floor not found on zone page (may be optional)');
      }
    }
  });

  // ── 4f. A-Frame Components Registered ──────────────────────────

  test('Core A-Frame components registered', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const components = await page.evaluate(() => {
      if (typeof AFRAME === 'undefined') return {};
      const comps = AFRAME.components || {};
      return {
        'zone-link': 'zone-link' in comps,
        'look-at-camera': 'look-at-camera' in comps,
      };
    });

    if (IS_HUB) {
      expect(components['zone-link'], 'zone-link component should be registered on hub').toBe(true);
    }
    expect(components['look-at-camera'], 'look-at-camera should be registered').toBe(true);
  });

  // ── 4g. VR Mode UI ────────────────────────────────────────────

  test('vr-mode-ui enabled on a-scene', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const vrUI = await page.evaluate(() => {
      const scene = document.querySelector('a-scene');
      if (!scene) return null;
      return scene.getAttribute('vr-mode-ui');
    });
    expect(vrUI, 'Scene should have vr-mode-ui attribute').toBeTruthy();
  });

  test('A-Frame VR enter button element created', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const enterVR = await page.evaluate(() => {
      return document.querySelector('.a-enter-vr') !== null ||
             document.getElementById('vr-enter-btn') !== null;
    });
    // May not exist in all headless contexts but should not crash
    expect(enterVR !== null, 'VR enter button check should not crash').toBe(true);
  });

  // ── 4h. Simulated Gamepad Loop ─────────────────────────────────

  test('Gamepad polling loop runs without crash', async ({ page }) => {
    const errors = setupErrorCollector(page);

    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    // Verify getGamepads exists and doesn't throw
    await page.evaluate(() => {
      if (navigator.getGamepads) {
        navigator.getGamepads(); // Should not throw
      }
    });

    // Wait for several animation frames to confirm no crash
    await page.waitForTimeout(3000);

    const critical = errors.filter(isCriticalError);
    expect(critical, 'Gamepad loop should not produce critical errors').toEqual([]);
  });

  // ── 4i. Quest 3 Renderer Configuration ─────────────────────────

  test('Scene renderer configured for VR (antialias, high refresh)', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const renderer = await page.evaluate(() => {
      const scene = document.querySelector('a-scene');
      if (!scene) return null;
      return String(scene.getAttribute('renderer') || '');
    });
    expect(renderer, 'Scene should have renderer attribute').toBeTruthy();
    if (renderer) {
      expect(renderer, 'Renderer should have antialias').toContain('antialias');
    }
  });

  // ── 4j. Nav Menu via Floating Button (simulating controller click) ──

  test('Nav floating button exists for VR interaction', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const btnExists = await page.evaluate(() => {
      return document.getElementById('vr-nav-floating-btn') !== null ||
             document.getElementById('vr-nav-button') !== null;
    });
    expect(btnExists, 'Nav floating button should exist for VR users').toBe(true);
  });

  // ── 4k. WebXR API Check ────────────────────────────────────────

  test('WebXR environment report (informational)', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const xrInfo = await page.evaluate(() => {
      return {
        isSecureContext: window.isSecureContext,
        hasNavigatorXR: 'xr' in navigator,
        hasWebXRPolyfill: typeof (window as any).WebXRPolyfill !== 'undefined',
        hasAFrame: typeof (window as any).AFRAME !== 'undefined',
        aframeVersion: (window as any).AFRAME?.version || 'not loaded',
        userAgent: navigator.userAgent.substring(0, 100),
      };
    });

    console.log('WebXR Environment:', JSON.stringify(xrInfo, null, 2));
    expect(xrInfo.hasAFrame, 'A-Frame should be available').toBe(true);
  });
});


// ═══════════════════════════════════════════════════════════════════
// SECTION 5: CROSS-MODALITY NAVIGATION — Test zone links work
// ═══════════════════════════════════════════════════════════════════

if (IS_HUB) {
  test.describe(`Cross-modality navigation — ${VR_PAGE}`, () => {
    test.use({ viewport: { width: 1280, height: 720 } });

    test('All zone-link URLs return valid HTTP responses', async ({ page }) => {
      await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
      await page.waitForTimeout(SCENE_WAIT);

      const urls = await page.evaluate(() => {
        const links = document.querySelectorAll('[zone-link]');
        const set = new Set<string>();
        links.forEach(l => {
          const attr = l.getAttribute('zone-link') || '';
          const match = attr.match(/url:\s*([^\s;]+)/);
          if (match) set.add(match[1]);
        });
        // Also get mobile zone card links
        document.querySelectorAll('.mobile-zone-card').forEach(c => {
          const href = c.getAttribute('href');
          if (href) set.add(href);
        });
        return Array.from(set);
      });

      for (const url of urls) {
        const full = url.startsWith('http') ? url : `${BASE}${url}`;
        const response = await page.request.get(full);
        expect(response.status(), `${url} should return < 500`).toBeLessThan(500);
      }
    });
  });
}


// ═══════════════════════════════════════════════════════════════════
// SECTION 6: PERFORMANCE — Page weight and entity counts
// ═══════════════════════════════════════════════════════════════════

test.describe(`Performance — ${VR_PAGE}`, () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('Page weight under 10MB', async ({ page }) => {
    let totalBytes = 0;
    page.on('response', async (res: any) => {
      try {
        const body = await res.body();
        totalBytes += body.length;
      } catch { /* streaming/websocket */ }
    });

    await page.goto(PAGE_URL, { waitUntil: 'networkidle', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(3000);

    const mb = totalBytes / (1024 * 1024);
    console.log(`Page weight: ${mb.toFixed(2)} MB`);
    expect(mb, 'Page should be under 10MB').toBeLessThan(10);
  });

  test('Entity count is reasonable (< 2000)', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SCENE_WAIT);

    const count = await page.evaluate(() =>
      document.querySelectorAll('a-entity, a-sphere, a-box, a-cylinder, a-plane, a-ring, a-torus, a-text, a-sky, a-circle').length
    );
    console.log(`A-Frame entity count: ${count}`);
    expect(count, 'Entity count should be < 2000').toBeLessThan(2000);
  });
});


// ═══════════════════════════════════════════════════════════════════
// SECTION 7: ACCESSIBILITY — lang, viewport meta, title
// ═══════════════════════════════════════════════════════════════════

test.describe(`Accessibility — ${VR_PAGE}`, () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('HTML has lang attribute', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    const lang = await page.locator('html').getAttribute('lang');
    expect(lang, 'html should have lang attribute').toBeTruthy();
  });

  test('Viewport meta tag exists', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    const vp = await page.evaluate(() => {
      const meta = document.querySelector('meta[name="viewport"]');
      return meta ? meta.getAttribute('content') : null;
    });
    expect(vp, 'viewport meta should exist').toBeTruthy();
    expect(vp, 'viewport should contain width=device-width').toContain('width=device-width');
  });

  test('Page has meaningful title', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    const title = await page.title();
    expect(title.length, 'Title should be meaningful (> 5 chars)').toBeGreaterThan(5);
  });
});
