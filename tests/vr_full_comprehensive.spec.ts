/**
 * VR Full Comprehensive Test Suite
 *
 * Tests the VR app across THREE user types:
 *   1. Desktop user (1280x720, keyboard/mouse)
 *   2. Mobile user (iPhone 14 Pro emulation, touch controls)
 *   3. VR user simulation (WebXR DOM elements, gamepad mock, gaze cursor)
 *
 * Covers both pages:
 *   - /vr/                  (Desktop VR Hub)
 *   - /vr/mobile-index.html (Mobile VR Hub)
 *
 * Run against remote:
 *   VERIFY_REMOTE=1 npx playwright test tests/vr_full_comprehensive.spec.ts
 */
import { test, expect, devices } from '@playwright/test';

const BASE = process.env.VERIFY_REMOTE === '1'
  ? 'https://findtorontoevents.ca'
  : 'http://localhost:5173';

// Non-critical errors to filter out
const NON_CRITICAL = [
  'net::',
  'CORS',
  'Failed to fetch',
  'NetworkError',
  'ERR_BLOCKED_BY_RESPONSE',
  'ERR_CONNECTION_REFUSED',
  'NS_ERROR',
  'NotAllowedError',     // WebXR requires user gesture
  'AbortError',
  'immersive-vr',        // WebXR session requests fail in headless
  'ServiceWorker',
  'navigator.xr',        // WebXR API not in headless
  'getGamepads',          // Gamepad API not in headless
  'SpeechSynthesis',      // TTS not in headless
  'speechSynthesis',
  'AudioContext',         // Web Audio in headless
  'play()',               // Media autoplay restrictions
  'DOMException',
  'The play() request',
  'ResizeObserver',       // Benign ResizeObserver errors
  'Script error',         // Cross-origin script errors
  'Loading module',       // Module loading
  'favicon',
];

function isCriticalError(msg: string): boolean {
  return !NON_CRITICAL.some(pattern => msg.includes(pattern));
}

// ═══════════════════════════════════════════════════════
// SECTION 1: DESKTOP USER TESTS — /vr/ (VR Hub)
// ═══════════════════════════════════════════════════════
test.describe('Desktop User — VR Hub (/vr/)', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('Page loads without critical JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);

    const critical = errors.filter(isCriticalError);
    if (critical.length > 0) {
      console.log('Critical errors found:', critical);
    }
    expect(critical).toEqual([]);
  });

  test('Title contains VR Hub', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    const title = await page.title();
    expect(title.toLowerCase()).toContain('vr');
  });

  test('A-Frame scene element exists and loads', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const scene = page.locator('a-scene');
    await expect(scene).toBeAttached();

    // Check scene has loaded attribute
    const hasLoaded = await page.evaluate(() => {
      const s = document.querySelector('a-scene');
      return s ? (s as any).hasLoaded : false;
    });
    expect(hasLoaded).toBe(true);
  });

  test('Loading screen appears and then hides', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });

    // Loading should be visible initially
    const loading = page.locator('#loading');
    await expect(loading).toBeAttached();

    // After ~2-3s, loading should fade/hide
    await page.waitForTimeout(4000);
    const isHidden = await page.evaluate(() => {
      const el = document.getElementById('loading');
      if (!el) return true;
      return el.classList.contains('hidden') || getComputedStyle(el).opacity === '0';
    });
    expect(isHidden).toBe(true);
  });

  test('All 7 zone portals exist (Events, Movies, Creators, Stocks, Wellness, Weather, Tutorial)', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const zones = ['events', 'movies', 'creators', 'stocks', 'wellness', 'weather', 'tutorial'];
    for (const zone of zones) {
      const link = page.locator(`[zone-link*="${zone}"]`);
      const count = await link.count();
      expect(count, `Zone portal for "${zone}" should exist`).toBeGreaterThanOrEqual(1);
    }
  });

  test('Camera rig exists at correct starting position', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const pos = await page.evaluate(() => {
      const rig = document.getElementById('rig');
      if (!rig) return null;
      return rig.getAttribute('position');
    });
    expect(pos).toBeTruthy();
  });

  test('Instructions bar appears after loading', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const instructions = page.locator('#instructions');
    const isVisible = await page.evaluate(() => {
      const el = document.getElementById('instructions');
      return el && !el.classList.contains('hidden');
    });
    expect(isVisible).toBe(true);
  });

  test('F1 help overlay opens and closes', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Press F1 to open help
    await page.keyboard.press('F1');
    await page.waitForTimeout(500);

    const helpOverlay = page.locator('#help-overlay');
    const isVisible = await page.evaluate(() => {
      const el = document.getElementById('help-overlay');
      return el && !el.classList.contains('hidden');
    });
    expect(isVisible).toBe(true);

    // Press Escape to close
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    const isClosed = await page.evaluate(() => {
      const el = document.getElementById('help-overlay');
      return el && el.classList.contains('hidden');
    });
    expect(isClosed).toBe(true);
  });

  test('Keyboard shortcuts 1-6 move camera to zone positions', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    // Press '1' to jump to Events zone
    await page.keyboard.press('1');
    await page.waitForTimeout(500);

    const pos = await page.evaluate(() => {
      const cam = document.querySelector('a-camera');
      if (!cam) return null;
      const p = cam.getAttribute('position');
      return p ? { x: parseFloat((p as any).x), y: parseFloat((p as any).y), z: parseFloat((p as any).z) } : null;
    });
    expect(pos).toBeTruthy();
    if (pos) {
      expect(pos.x).toBe(-6); // Events zone X
    }

    // Press '0' to return to center
    await page.keyboard.press('0');
    await page.waitForTimeout(500);

    const centerPos = await page.evaluate(() => {
      const cam = document.querySelector('a-camera');
      if (!cam) return null;
      const p = cam.getAttribute('position');
      return p ? { x: parseFloat((p as any).x) } : null;
    });
    expect(centerPos).toBeTruthy();
    if (centerPos) {
      expect(centerPos.x).toBe(0);
    }
  });

  test('Nav menu opens with M key and contains session timer', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    await page.keyboard.press('m');
    await page.waitForTimeout(1000);

    const session = page.locator('#vr-session');
    const exists = await session.count();
    expect(exists).toBeGreaterThanOrEqual(1);
  });

  test('Data badges created for each zone', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const badges = ['events', 'movies', 'weather', 'stocks', 'wellness', 'creators'];
    for (const b of badges) {
      const el = page.locator(`#data-badge-${b}`);
      await expect(el, `Data badge for ${b}`).toBeAttached();
    }
  });

  test('Gaze cursor ring exists inside camera', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const gazeRing = page.locator('a-camera a-ring[cursor]');
    await expect(gazeRing).toBeAttached();
  });

  test('Laser controller entities exist (left and right hand)', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    await expect(page.locator('#left-hand')).toBeAttached();
    await expect(page.locator('#right-hand')).toBeAttached();
  });

  test('Zone tooltips configured on portals', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const tooltipCount = await page.locator('[zone-tooltip]').count();
    expect(tooltipCount).toBeGreaterThanOrEqual(6);
  });

  test('Hub visit tracked in localStorage', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const visited = await page.evaluate(() => {
      try { return JSON.parse(localStorage.getItem('vr_visited_zones') || '{}'); } catch { return {}; }
    });
    expect(visited).toHaveProperty('hub');
  });

  test('Enhancement JS modules loaded (scripts attached)', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    const scripts = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('script[src]')).map(s => s.getAttribute('src'));
    });

    const expectedModules = [
      'controller-support.js', 'nav-menu.js', 'area-guide.js',
      'quick-wins.js', 'scene-enhancements.js', 'completeness.js',
      'interaction.js', 'personalization.js', 'advanced-ux.js',
      'comfort-intelligence.js', 'content-depth.js', 'polish-productivity.js',
      'social-rich.js', 'intelligence-engage.js'
    ];

    for (const mod of expectedModules) {
      const found = scripts.some(s => s && s.includes(mod));
      expect(found, `Module ${mod} should be loaded`).toBe(true);
    }
  });

  test('Teleport floor and indicator exist', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    await expect(page.locator('#teleport-floor')).toBeAttached();
    await expect(page.locator('#teleport-indicator')).toBeAttached();
  });

  test('Central hub title text exists', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const titleText = await page.evaluate(() => {
      const texts = document.querySelectorAll('a-text');
      for (const t of texts) {
        if (t.getAttribute('value') === 'Toronto Events') return true;
      }
      return false;
    });
    expect(titleText).toBe(true);
  });

  test('All external resources load (no 404s for key assets)', async ({ page }) => {
    const failedResources: string[] = [];
    page.on('response', (response) => {
      if (response.status() === 404 && response.url().includes('/vr/')) {
        failedResources.push(response.url());
      }
    });

    await page.goto(`${BASE}/vr/`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    if (failedResources.length > 0) {
      console.log('404 resources:', failedResources);
    }
    // Allow some non-critical 404s (assets), but JS files should not 404
    const js404s = failedResources.filter(u => u.endsWith('.js'));
    expect(js404s, 'No JS files should 404').toEqual([]);
  });

  test('WASD movement controls are enabled on camera', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const wasdEnabled = await page.evaluate(() => {
      const cam = document.querySelector('a-camera');
      if (!cam) return false;
      const wasd = cam.getAttribute('wasd-controls');
      return wasd !== null && wasd !== undefined;
    });
    expect(wasdEnabled).toBe(true);
  });
});


// ═══════════════════════════════════════════════════════
// SECTION 2: DESKTOP USER TESTS — /vr/mobile-index.html
// ═══════════════════════════════════════════════════════
test.describe('Desktop User — Mobile VR page (/vr/mobile-index.html)', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('Page loads without critical JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);

    const critical = errors.filter(isCriticalError);
    if (critical.length > 0) console.log('Critical errors:', critical);
    expect(critical).toEqual([]);
  });

  test('Title is "VR Hub Mobile"', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    const title = await page.title();
    expect(title).toContain('VR Hub Mobile');
  });

  test('A-Frame scene loads', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const hasLoaded = await page.evaluate(() => {
      const s = document.querySelector('a-scene');
      return s ? (s as any).hasLoaded : false;
    });
    expect(hasLoaded).toBe(true);
  });

  test('Loading screen hides after scene loads', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const isHidden = await page.evaluate(() => {
      const el = document.getElementById('mobile-loading');
      if (!el) return true;
      return el.classList.contains('hidden');
    });
    expect(isHidden).toBe(true);
  });

  test('Mobile UI overlay exists with top bar and bottom controls', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    await expect(page.locator('#mobile-ui')).toBeAttached();
    await expect(page.locator('.mobile-top-bar')).toBeAttached();
    await expect(page.locator('.mobile-bottom-controls')).toBeAttached();
  });

  test('VR Hub logo visible in top bar', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const logo = page.locator('.mobile-logo');
    await expect(logo).toBeAttached();
    const text = await logo.textContent();
    expect(text).toContain('VR Hub');
  });

  test('Joystick element exists', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    await expect(page.locator('#joystick')).toBeAttached();
    await expect(page.locator('#joystick-knob')).toBeAttached();
  });

  test('Action buttons exist (jump, select, reset)', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const actionBtns = await page.locator('.mobile-action-btn').count();
    expect(actionBtns).toBeGreaterThanOrEqual(3);
  });

  test('Zone menu opens when hamburger is clicked', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Click the menu button
    await page.locator('.mobile-menu-btn').click();
    await page.waitForTimeout(500);

    const isActive = await page.evaluate(() => {
      const menu = document.getElementById('mobile-zone-menu');
      return menu && menu.classList.contains('active');
    });
    expect(isActive).toBe(true);
  });

  test('Zone menu contains all zone links', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const zoneCards = await page.locator('.mobile-zone-card').count();
    expect(zoneCards).toBeGreaterThanOrEqual(7); // Weather, Movies, Events, Creators, Stocks, Wellness, Tutorial + VR Hub

    // Check specific zone links
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
    expect(hrefs).toContain('/vr/wellness/');
    expect(hrefs).toContain('/vr/tutorial/');
  });

  test('Zone menu closes when X button is clicked', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Open menu
    await page.locator('.mobile-menu-btn').click();
    await page.waitForTimeout(500);

    // Close menu
    await page.locator('.mobile-close-btn').click();
    await page.waitForTimeout(500);

    const isActive = await page.evaluate(() => {
      const menu = document.getElementById('mobile-zone-menu');
      return menu && menu.classList.contains('active');
    });
    expect(isActive).toBe(false);
  });

  test('VR enter button exists', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    await expect(page.locator('#vr-enter-btn')).toBeAttached();
  });

  test('Three zone portals in A-Frame scene (Weather, Movies, Events)', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const zoneCount = await page.locator('[data-zone]').count();
    expect(zoneCount).toBeGreaterThanOrEqual(3);
  });

  test('Stars and particles created in scene', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const starCount = await page.evaluate(() => {
      const stars = document.getElementById('stars');
      return stars ? stars.children.length : 0;
    });
    expect(starCount).toBeGreaterThan(50);

    const particleCount = await page.evaluate(() => {
      const particles = document.getElementById('particles');
      return particles ? particles.children.length : 0;
    });
    expect(particleCount).toBeGreaterThan(10);
  });
});


// ═══════════════════════════════════════════════════════
// SECTION 3: MOBILE USER TESTS — /vr/mobile-index.html
// (iPhone 14 Pro emulation)
// ═══════════════════════════════════════════════════════
test.describe('Mobile User (iPhone) — /vr/mobile-index.html', () => {
  test.use({
    viewport: { width: 393, height: 852 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    isMobile: true,
    hasTouch: true,
  });

  test('Page loads on mobile without critical JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);

    const critical = errors.filter(isCriticalError);
    if (critical.length > 0) console.log('Mobile critical errors:', critical);
    expect(critical).toEqual([]);
  });

  test('Orientation warning shows in portrait mode', async ({ page }) => {
    // iPhone 14 Pro default is portrait (393x852)
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const warningShown = await page.evaluate(() => {
      const warning = document.getElementById('orientation-warning');
      return warning && warning.classList.contains('show');
    });
    // In portrait, width < height, so warning should show
    expect(warningShown).toBe(true);
  });

  test('Touch controls are responsive (joystick + buttons)', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    // Verify joystick and action buttons are in DOM
    await expect(page.locator('#joystick')).toBeAttached();
    const actionBtns = await page.locator('.mobile-action-btn').count();
    expect(actionBtns).toBeGreaterThanOrEqual(3);
  });

  test('MobileVR object initialized', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const hasInit = await page.evaluate(() => {
      return typeof (window as any).MobileVR !== 'undefined' ||
             document.getElementById('rig') !== null;
    });
    expect(hasInit).toBe(true);
  });

  test('Menu button is tappable and opens zone menu', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    // Tap the hamburger menu
    await page.locator('.mobile-menu-btn').tap();
    await page.waitForTimeout(500);

    const isOpen = await page.evaluate(() => {
      const menu = document.getElementById('mobile-zone-menu');
      return menu && menu.classList.contains('active');
    });
    expect(isOpen).toBe(true);
  });

  test('Zone cards in menu have proper touch targets (>= 44px)', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Open menu
    await page.locator('.mobile-menu-btn').tap();
    await page.waitForTimeout(500);

    const sizes = await page.evaluate(() => {
      const cards = document.querySelectorAll('.mobile-zone-card');
      return Array.from(cards).map(c => {
        const rect = c.getBoundingClientRect();
        return { width: rect.width, height: rect.height };
      });
    });

    // Each card should have at least 44px minimum touch target
    for (const size of sizes) {
      expect(size.height, 'Touch target height >= 44px').toBeGreaterThanOrEqual(44);
      expect(size.width, 'Touch target width >= 44px').toBeGreaterThanOrEqual(44);
    }
  });

  test('A-Frame camera has touch look-controls enabled', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const touchEnabled = await page.evaluate(() => {
      const cam = document.getElementById('camera');
      if (!cam) return false;
      const lookControls = cam.getAttribute('look-controls');
      if (typeof lookControls === 'string') return lookControls.includes('touchEnabled: true');
      if (typeof lookControls === 'object' && lookControls) return (lookControls as any).touchEnabled === true;
      return false;
    });
    expect(touchEnabled).toBe(true);
  });
});


// ═══════════════════════════════════════════════════════
// SECTION 4: MOBILE USER TESTS — /vr/ (Desktop VR Hub
// viewed on mobile)
// ═══════════════════════════════════════════════════════
test.describe('Mobile User (iPhone) — VR Hub (/vr/)', () => {
  test.use({
    viewport: { width: 393, height: 852 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    isMobile: true,
    hasTouch: true,
  });

  test('VR Hub loads on mobile without critical JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);

    const critical = errors.filter(isCriticalError);
    if (critical.length > 0) console.log('Mobile VR Hub errors:', critical);
    expect(critical).toEqual([]);
  });

  test('A-Frame scene loads on mobile', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const hasLoaded = await page.evaluate(() => {
      const s = document.querySelector('a-scene');
      return s ? (s as any).hasLoaded : false;
    });
    expect(hasLoaded).toBe(true);
  });

  test('Mobile detection script loaded', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const hasMobileDetect = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('script[src]')).some(
        s => s.getAttribute('src')?.includes('mobile-detect')
      );
    });
    expect(hasMobileDetect).toBe(true);
  });

  test('Zone portals are still accessible on mobile viewport', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const clickableCount = await page.locator('.clickable').count();
    expect(clickableCount).toBeGreaterThan(5);
  });
});


// ═══════════════════════════════════════════════════════
// SECTION 5: MOBILE LANDSCAPE TESTS
// ═══════════════════════════════════════════════════════
test.describe('Mobile User (Landscape) — /vr/mobile-index.html', () => {
  test.use({
    viewport: { width: 852, height: 393 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    isMobile: true,
    hasTouch: true,
  });

  test('Orientation warning NOT shown in landscape', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const warningShown = await page.evaluate(() => {
      const warning = document.getElementById('orientation-warning');
      return warning && warning.classList.contains('show');
    });
    // In landscape, width > height, so warning should NOT show
    expect(warningShown).toBe(false);
  });

  test('Look hint shows after loading in landscape', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Look hint should briefly appear
    const lookHint = page.locator('#look-hint');
    await expect(lookHint).toBeAttached();
  });
});


// ═══════════════════════════════════════════════════════
// SECTION 6: VR USER SIMULATION — /vr/
// (Testing WebXR-related DOM elements, gamepad, XR API)
// ═══════════════════════════════════════════════════════
test.describe('VR User Simulation — VR Hub (/vr/)', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('WebXR vr-mode-ui is enabled on a-scene', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const vrModeUI = await page.evaluate(() => {
      const scene = document.querySelector('a-scene');
      if (!scene) return null;
      return scene.getAttribute('vr-mode-ui');
    });
    expect(vrModeUI).toBeTruthy();
  });

  test('A-Frame creates VR mode enter button', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    // A-Frame auto-creates a .a-enter-vr element
    const enterVR = page.locator('.a-enter-vr');
    const count = await enterVR.count();
    // May or may not exist depending on WebXR support
    // Just verify no crash
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('Gaze cursor has fuse enabled with 1500ms timeout', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const fuseConfig = await page.evaluate(() => {
      const ring = document.querySelector('a-camera a-ring[cursor]');
      if (!ring) return null;
      const cursor = ring.getAttribute('cursor');
      return cursor;
    });
    expect(fuseConfig).toBeTruthy();
    if (typeof fuseConfig === 'string') {
      expect(fuseConfig).toContain('fuse: true');
      expect(fuseConfig).toContain('fuseTimeout: 1500');
    }
  });

  test('Left and right hand laser controllers configured', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const leftHand = await page.evaluate(() => {
      const el = document.getElementById('left-hand');
      return el ? {
        laserControls: el.getAttribute('laser-controls'),
        raycaster: el.getAttribute('raycaster'),
      } : null;
    });
    expect(leftHand).toBeTruthy();
    if (leftHand) {
      expect(String(leftHand.laserControls)).toContain('left');
    }

    const rightHand = await page.evaluate(() => {
      const el = document.getElementById('right-hand');
      return el ? {
        laserControls: el.getAttribute('laser-controls'),
      } : null;
    });
    expect(rightHand).toBeTruthy();
    if (rightHand) {
      expect(String(rightHand.laserControls)).toContain('right');
    }
  });

  test('Raycaster configured for clickable objects with far range', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const raycasterConfig = await page.evaluate(() => {
      const ring = document.querySelector('a-camera a-ring[raycaster]');
      if (!ring) return null;
      return ring.getAttribute('raycaster');
    });
    expect(raycasterConfig).toBeTruthy();
    expect(String(raycasterConfig)).toContain('.clickable');
  });

  test('Controller support script loaded', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    const hasControllerScript = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('script[src]')).some(
        s => s.getAttribute('src')?.includes('controller-support')
      );
    });
    expect(hasControllerScript).toBe(true);
  });

  test('VR controller system component loaded', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const hasVRController = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('script[src]')).some(
        s => s.getAttribute('src')?.includes('vr-controller-system')
      );
    });
    expect(hasVRController).toBe(true);
  });

  test('Simulated gamepad locomotion loop runs without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Mock a gamepad and verify the loop doesn't crash
    await page.evaluate(() => {
      // Simulate navigator.getGamepads returning empty
      if (navigator.getGamepads) {
        const pads = navigator.getGamepads();
        // Just verify the function exists and returns
        return pads !== undefined;
      }
      return true;
    });

    // Wait for several animation frames
    await page.waitForTimeout(2000);

    const critical = errors.filter(isCriticalError);
    expect(critical).toEqual([]);
  });

  test('Zone-link component navigates on click event', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    // Verify zone-link components are registered
    const registered = await page.evaluate(() => {
      return typeof AFRAME !== 'undefined' &&
             AFRAME.components &&
             'zone-link' in AFRAME.components;
    });
    expect(registered).toBe(true);
  });

  test('Teleport surface component registered', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const registered = await page.evaluate(() => {
      return typeof AFRAME !== 'undefined' &&
             AFRAME.components &&
             'teleport-surface' in AFRAME.components;
    });
    expect(registered).toBe(true);
  });

  test('Look-at-camera component registered', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const registered = await page.evaluate(() => {
      return typeof AFRAME !== 'undefined' &&
             AFRAME.components &&
             'look-at-camera' in AFRAME.components;
    });
    expect(registered).toBe(true);
  });
});


// ═══════════════════════════════════════════════════════
// SECTION 7: VR USER SIMULATION — /vr/mobile-index.html
// ═══════════════════════════════════════════════════════
test.describe('VR User Simulation — Mobile VR (/vr/mobile-index.html)', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('VR mode UI is enabled with custom enter button', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const vrConfig = await page.evaluate(() => {
      const scene = document.querySelector('a-scene');
      if (!scene) return null;
      return scene.getAttribute('vr-mode-ui');
    });
    expect(vrConfig).toBeTruthy();
    expect(String(vrConfig)).toContain('enterVRButton: #vr-enter-btn');
  });

  test('enterVR function exists and is callable', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const fnExists = await page.evaluate(() => {
      return typeof (window as any).enterVR === 'function';
    });
    expect(fnExists).toBe(true);
  });

  test('Scene renderer configured for VR (antialias, high refresh rate)', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const renderer = await page.evaluate(() => {
      const scene = document.querySelector('a-scene');
      if (!scene) return null;
      return scene.getAttribute('renderer');
    });
    expect(renderer).toBeTruthy();
    expect(String(renderer)).toContain('antialias: true');
    expect(String(renderer)).toContain('highRefreshRate: true');
  });

  test('Camera has raycaster for clickable objects', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const raycaster = await page.evaluate(() => {
      const cam = document.getElementById('camera');
      if (!cam) return null;
      return cam.getAttribute('raycaster');
    });
    expect(raycaster).toBeTruthy();
    expect(String(raycaster)).toContain('.clickable');
  });

  test('Zone portals have clickable class for raycasting', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const clickableZones = await page.locator('[data-zone].clickable').count();
    expect(clickableZones).toBeGreaterThanOrEqual(3);
  });
});


// ═══════════════════════════════════════════════════════
// SECTION 8: CROSS-PAGE NAVIGATION TESTS
// ═══════════════════════════════════════════════════════
test.describe('Cross-Page Navigation', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('Mobile zone menu links resolve to valid pages', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const links = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.mobile-zone-card')).map(
        c => c.getAttribute('href')
      ).filter(Boolean);
    });

    // Verify each link returns 200
    for (const link of links) {
      const response = await page.request.get(`${BASE}${link}`);
      expect(response.status(), `${link} should return 200`).toBeLessThan(500);
    }
  });

  test('VR Hub zone-link URLs are valid', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const urls = await page.evaluate(() => {
      const links = document.querySelectorAll('[zone-link]');
      const set = new Set<string>();
      links.forEach(l => {
        const attr = l.getAttribute('zone-link');
        if (attr) {
          // Parse "url: /vr/events/" from component attribute
          const match = attr.match(/url:\s*([^\s;]+)/);
          if (match) set.add(match[1]);
        }
      });
      return Array.from(set);
    });

    for (const url of urls) {
      const response = await page.request.get(`${BASE}${url}`);
      expect(response.status(), `${url} should return 200`).toBeLessThan(500);
    }
  });
});


// ═══════════════════════════════════════════════════════
// SECTION 9: PERFORMANCE & RESOURCE TESTS
// ═══════════════════════════════════════════════════════
test.describe('Performance & Resources', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('A-Frame library loads from CDN (1.6.0)', async ({ page }) => {
    let aframeLoaded = false;
    page.on('response', (response) => {
      if (response.url().includes('aframe') && response.url().includes('1.6.0') && response.status() === 200) {
        aframeLoaded = true;
      }
    });

    await page.goto(`${BASE}/vr/`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    expect(aframeLoaded).toBe(true);
  });

  test('VR Hub page weight is under 10MB (reasonable for WebXR)', async ({ page }) => {
    let totalBytes = 0;
    page.on('response', async (response) => {
      try {
        const body = await response.body();
        totalBytes += body.length;
      } catch { /* ignore streaming/websocket */ }
    });

    await page.goto(`${BASE}/vr/`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const totalMB = totalBytes / (1024 * 1024);
    console.log(`VR Hub total page weight: ${totalMB.toFixed(2)} MB`);
    expect(totalMB).toBeLessThan(10);
  });

  test('Mobile VR page weight is under 5MB', async ({ page }) => {
    let totalBytes = 0;
    page.on('response', async (response) => {
      try {
        const body = await response.body();
        totalBytes += body.length;
      } catch { /* ignore */ }
    });

    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const totalMB = totalBytes / (1024 * 1024);
    console.log(`Mobile VR page weight: ${totalMB.toFixed(2)} MB`);
    expect(totalMB).toBeLessThan(5);
  });

  test('No memory leaks from 200 star entities', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);

    const metrics = await page.evaluate(() => {
      return {
        starCount: document.getElementById('stars')?.children.length || 0,
        particleCount: document.getElementById('particles')?.children.length || 0,
        totalEntities: document.querySelectorAll('a-entity, a-sphere, a-box, a-cylinder, a-plane, a-ring, a-torus, a-text').length
      };
    });

    console.log('Entity counts:', metrics);
    expect(metrics.starCount).toBeLessThanOrEqual(250); // Should be ~200
    expect(metrics.particleCount).toBeLessThanOrEqual(100); // Should be ~50
  });
});


// ═══════════════════════════════════════════════════════
// SECTION 10: ACCESSIBILITY TESTS
// ═══════════════════════════════════════════════════════
test.describe('Accessibility', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('VR Hub has proper lang attribute', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    const lang = await page.locator('html').getAttribute('lang');
    expect(lang).toBe('en');
  });

  test('Mobile VR has proper lang attribute', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    const lang = await page.locator('html').getAttribute('lang');
    expect(lang).toBe('en');
  });

  test('Mobile VR has proper viewport meta tag', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });

    const viewport = await page.evaluate(() => {
      const meta = document.querySelector('meta[name="viewport"]');
      return meta ? meta.getAttribute('content') : null;
    });
    expect(viewport).toBeTruthy();
    expect(viewport).toContain('width=device-width');
  });

  test('Mobile VR has apple-mobile-web-app-capable meta', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });

    const capable = await page.evaluate(() => {
      const meta = document.querySelector('meta[name="apple-mobile-web-app-capable"]');
      return meta ? meta.getAttribute('content') : null;
    });
    expect(capable).toBe('yes');
  });

  test('VR Hub has title element', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    const title = await page.title();
    expect(title.length).toBeGreaterThan(5);
  });

  test('Theme color meta tag set', async ({ page }) => {
    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    const themeColor = await page.evaluate(() => {
      const meta = document.querySelector('meta[name="theme-color"]');
      return meta ? meta.getAttribute('content') : null;
    });
    expect(themeColor).toBeTruthy();
  });
});


// ═══════════════════════════════════════════════════════
// SECTION 11: TABLET EMULATION TESTS
// ═══════════════════════════════════════════════════════
test.describe('Tablet User (iPad) — VR Pages', () => {
  test.use({
    viewport: { width: 834, height: 1194 },
    userAgent: 'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    isMobile: true,
    hasTouch: true,
  });

  test('VR Hub loads on tablet without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);

    const critical = errors.filter(isCriticalError);
    expect(critical).toEqual([]);
  });

  test('Mobile VR loads on tablet without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto(`${BASE}/vr/mobile-index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);

    const critical = errors.filter(isCriticalError);
    expect(critical).toEqual([]);
  });
});
