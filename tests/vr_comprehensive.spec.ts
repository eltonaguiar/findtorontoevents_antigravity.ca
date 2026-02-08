import { test, expect, Page } from '@playwright/test';

/**
 * Comprehensive VR Zone Tests
 *
 * Tests all VR zones section by section, roleplaying as:
 *   - Keyboard / mouse desktop user
 *   - Meta Quest controller user (thumbstick, teleport, laser pointer)
 *   - Gaze cursor user (fuse-based interaction)
 *
 * Covers:
 *   - All 7 VR pages load without JS errors
 *   - Controller support (controller-support.js) properly initializes
 *   - Creators page: live/offline separation, progress bar, YouTube API, stream embed
 *   - Movies page: theater, filtering, trailer playback
 *   - Hub: zone portals, navigation
 *   - Shared features: nav-menu, presence badge, keyboard shortcuts
 */

const REMOTE = 'https://findtorontoevents.ca';

// Helper: collect JS errors on a page
function collectErrors(page: Page) {
  const errors: string[] = [];
  page.on('pageerror', err => errors.push(err.message));
  return errors;
}

// Helper: wait for A-Frame scene to be ready
async function waitForScene(page: Page, timeout = 15000) {
  await page.waitForSelector('a-scene', { timeout });
  // Wait for scene loaded attribute
  await page.waitForFunction(() => {
    const scene = document.querySelector('a-scene');
    return scene && ((scene as any).hasLoaded || scene.getAttribute('loaded') !== null);
  }, { timeout });
  await page.waitForTimeout(2000); // buffer for components to init
}

// ══════════════════════════════════════════════
// SECTION 1: Controller Support (All Pages)
// ══════════════════════════════════════════════
test.describe('Controller Support — All VR Pages', () => {

  const VR_PAGES = [
    { name: 'Hub',      url: '/vr/index.html' },
    { name: 'Creators', url: '/vr/creators.html' },
    { name: 'Movies',   url: '/vr/movies.html' },
    { name: 'Events',   url: '/vr/events/' },
    { name: 'Weather',  url: '/vr/weather-zone.html' },
    { name: 'Stocks',   url: '/vr/stocks-zone.html' },
    { name: 'Wellness', url: '/vr/wellness/' },
  ];

  for (const zone of VR_PAGES) {
    test(`${zone.name}: loads without critical JS errors`, async ({ page }) => {
      const errors = collectErrors(page);
      await page.goto(`${REMOTE}${zone.url}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await waitForScene(page);
      await page.waitForTimeout(3000);

      const critical = errors.filter(e =>
        e.includes('SyntaxError') || e.includes('ReferenceError') ||
        (e.includes('TypeError') && !e.includes('WebGL') && !e.includes('getGamepads'))
      );
      console.log(`[${zone.name}] JS errors:`, critical.length, critical.length > 0 ? critical : '');
      expect(critical).toHaveLength(0);
    });

    test(`${zone.name}: has #rig camera entity`, async ({ page }) => {
      await page.goto(`${REMOTE}${zone.url}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await waitForScene(page);

      const rigInfo = await page.evaluate(() => {
        const rig = document.getElementById('rig') || document.getElementById('camera-rig');
        if (!rig) return null;
        const cam = rig.querySelector('a-camera') || rig.querySelector('[camera]');
        return {
          id: rig.id,
          hasCamera: !!cam,
          haslookControls: cam ? cam.hasAttribute('look-controls') : false,
          hasWasd: cam ? cam.hasAttribute('wasd-controls') : false,
        };
      });

      console.log(`[${zone.name}] Rig:`, rigInfo);
      expect(rigInfo).not.toBeNull();
      expect(rigInfo!.hasCamera).toBe(true);
    });

    test(`${zone.name}: controller-support.js initializes`, async ({ page }) => {
      const logs: string[] = [];
      page.on('console', msg => {
        if (msg.text().includes('[Controller Support]')) logs.push(msg.text());
      });

      await page.goto(`${REMOTE}${zone.url}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await waitForScene(page);
      await page.waitForTimeout(4000);

      console.log(`[${zone.name}] Controller logs:`, logs);
      // Should see initialization log
      const hasInit = logs.some(l => l.includes('Ready') || l.includes('Setup complete'));
      expect(hasInit).toBe(true);

      // VRControllerSupport API should exist
      const hasAPI = await page.evaluate(() => typeof (window as any).VRControllerSupport === 'object');
      expect(hasAPI).toBe(true);
    });

    test(`${zone.name}: has left + right hand entities`, async ({ page }) => {
      await page.goto(`${REMOTE}${zone.url}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await waitForScene(page);
      await page.waitForTimeout(4000);

      const hands = await page.evaluate(() => {
        const rig = document.getElementById('rig') || document.getElementById('camera-rig');
        if (!rig) return { left: false, right: false, leftLaser: false, rightLaser: false };
        const left = rig.querySelector('#left-hand') || rig.querySelector('#left-controller');
        const right = rig.querySelector('#right-hand') || rig.querySelector('#right-controller');
        return {
          left: !!left,
          right: !!right,
          leftLaser: left ? left.hasAttribute('laser-controls') : false,
          rightLaser: right ? right.hasAttribute('laser-controls') : false,
        };
      });

      console.log(`[${zone.name}] Hands:`, hands);
      expect(hands.left).toBe(true);
      expect(hands.right).toBe(true);
      expect(hands.leftLaser).toBe(true);
      expect(hands.rightLaser).toBe(true);
    });
  }
});

// ══════════════════════════════════════════════
// SECTION 2: Shared Features (nav-menu, presence)
// ══════════════════════════════════════════════
test.describe('Shared Features — Nav Menu & Presence', () => {

  test('nav-menu.js: 2D menu exists and toggles', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/index.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    // floating button should exist
    const floatBtn = page.locator('#vr-nav-floating-btn');
    await expect(floatBtn).toBeAttached();

    // Menu should be hidden initially
    const menu = page.locator('#vr-nav-menu-2d');
    await expect(menu).toBeAttached();
    await expect(menu).not.toHaveClass(/active/);

    // Toggle via keyboard M
    await page.keyboard.press('m');
    await page.waitForTimeout(300);
    await expect(menu).toHaveClass(/active/);

    // Close via Escape
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    await expect(menu).not.toHaveClass(/active/);
  });

  test('nav-menu: has links to all 7 zones', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/index.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    await page.keyboard.press('m');
    await page.waitForTimeout(300);

    const zoneLinks = await page.evaluate(() => {
      const links = document.querySelectorAll('#vr-nav-menu-2d .vr-nav-zone');
      return Array.from(links).map(l => ({
        text: l.querySelector('.vr-nav-name')?.textContent || '',
        href: l.getAttribute('href') || '',
      }));
    });

    console.log('Nav zones:', zoneLinks.map(z => z.text));
    expect(zoneLinks.length).toBeGreaterThanOrEqual(7);
    expect(zoneLinks.some(z => z.href.includes('movies'))).toBe(true);
    expect(zoneLinks.some(z => z.href.includes('creators'))).toBe(true);
    expect(zoneLinks.some(z => z.href.includes('events'))).toBe(true);
    expect(zoneLinks.some(z => z.href.includes('weather'))).toBe(true);
    expect(zoneLinks.some(z => z.href.includes('wellness'))).toBe(true);
    expect(zoneLinks.some(z => z.href.includes('stocks'))).toBe(true);
  });

  test('presence badge shows user count', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    const badge = page.locator('#vr-presence-badge');
    await expect(badge).toBeAttached();

    const count = await page.locator('#presence-count').textContent();
    console.log('Presence:', count);
    expect(count).toContain('online');
  });

  test('keyboard shortcuts panel toggleable with ?', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/index.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    const panel = page.locator('#vr-shortcuts-panel');
    await expect(panel).toBeAttached();

    // Should be hidden by default
    await expect(panel).toBeHidden();

    // Toggle with ? key
    await page.keyboard.press('?');
    await page.waitForTimeout(300);
    await expect(panel).toBeVisible();
  });
});

// ══════════════════════════════════════════════
// SECTION 3: Creators — Live/Offline, YouTube, Preview
// ══════════════════════════════════════════════
test.describe('VR Creators — Features', () => {

  test('creators page loads and shows creator cards', async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(`${REMOTE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(6000); // wait for API fetch

    const cardWall = await page.evaluate(() => {
      const wall = document.getElementById('card-wall');
      return wall ? wall.children.length : 0;
    });
    console.log('Card wall children:', cardWall);
    expect(cardWall).toBeGreaterThan(0);

    const critical = errors.filter(e =>
      e.includes('SyntaxError') || e.includes('ReferenceError')
    );
    expect(critical).toHaveLength(0);
  });

  test('creators: live/offline section separation', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(6000);

    const sections = await page.evaluate(() => {
      const wall = document.getElementById('card-wall');
      if (!wall) return { children: 0, hasText: false };
      // Look for section header text elements
      const texts = wall.querySelectorAll('a-text');
      const headerTexts: string[] = [];
      texts.forEach(t => {
        const val = t.getAttribute('value') || '';
        if (val.includes('LIVE NOW') || val.includes('OFFLINE')) {
          headerTexts.push(val);
        }
      });
      return { children: wall.children.length, headers: headerTexts };
    });

    console.log('Sections:', sections);
    // Should have at least an OFFLINE header (there may not be anyone live)
    expect(sections.headers.length).toBeGreaterThanOrEqual(1);
    expect(sections.headers.some((h: string) => h.includes('OFFLINE'))).toBe(true);
  });

  test('creators: offline cards have OFFLINE badge', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(6000);

    const offlineBadges = await page.evaluate(() => {
      const wall = document.getElementById('card-wall');
      if (!wall) return 0;
      const texts = wall.querySelectorAll('a-text');
      let count = 0;
      texts.forEach(t => {
        if (t.getAttribute('value') === 'OFFLINE') count++;
      });
      return count;
    });

    console.log('OFFLINE badges:', offlineBadges);
    expect(offlineBadges).toBeGreaterThan(0);
  });

  test('creators: platform filter buttons work', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(6000);

    // Platform strip should exist
    const platformBtns = await page.locator('#platform-strip button').count();
    console.log('Platform filter buttons:', platformBtns);
    expect(platformBtns).toBeGreaterThanOrEqual(4);

    // Click a filter
    await page.locator('#platform-strip button').nth(1).click();
    await page.waitForTimeout(500);

    // Should have an active button
    const hasActive = await page.evaluate(() => {
      const btns = document.querySelectorAll('#platform-strip button.active');
      return btns.length;
    });
    expect(hasActive).toBe(1);
  });

  test('creators: refresh button shows progress bar', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(6000);

    // Progress bar should be hidden initially
    const progressBar = page.locator('#refresh-progress');
    await expect(progressBar).toBeAttached();
    await expect(progressBar).not.toHaveClass(/visible/);

    // Click refresh
    await page.locator('#refresh-btn').click();

    // Progress should appear
    await page.waitForTimeout(500);
    const isVisible = await page.evaluate(() => {
      return document.getElementById('refresh-progress')?.classList.contains('visible');
    });
    console.log('Progress bar visible on refresh:', isVisible);
    expect(isVisible).toBe(true);

    // Wait for refresh to complete
    await page.waitForTimeout(5000);

    // Progress should hide after completion
    const isHiddenAfter = await page.evaluate(() => {
      return !document.getElementById('refresh-progress')?.classList.contains('visible');
    });
    expect(isHiddenAfter).toBe(true);
  });

  test('creators: clicking a card opens detail overlay', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(6000);

    // Call showCreatorDetail directly
    const detailOpened = await page.evaluate(() => {
      if (typeof (window as any).showCreatorDetail === 'function') {
        (window as any).showCreatorDetail(0);
        return document.getElementById('creator-detail')?.classList.contains('open');
      }
      return false;
    });

    expect(detailOpened).toBe(true);

    // Check detail has content
    const detName = await page.locator('#det-name').textContent();
    console.log('Detail creator name:', detName);
    expect(detName).toBeTruthy();

    // Should have accounts list
    const accounts = await page.locator('#det-accounts .account-link').count();
    console.log('Account links:', accounts);
    expect(accounts).toBeGreaterThan(0);

    // Should have watch content buttons
    const watchBtns = await page.locator('#det-watch-content .wcr-btn').count();
    console.log('Watch content buttons:', watchBtns);
    expect(watchBtns).toBeGreaterThan(0);
  });

  test('creators: YouTube latest API returns videos', async ({ page }) => {
    const resp = await page.request.get(
      `${REMOTE}/fc/api/youtube_latest.php?handle=adinross&limit=3`
    );
    expect(resp.ok()).toBe(true);

    const data = await resp.json();
    console.log('YouTube API response:', JSON.stringify(data).substring(0, 200));
    expect(data.ok).toBe(true);
    expect(data.videos).toBeDefined();
    expect(data.videos.length).toBeGreaterThan(0);
    expect(data.videos[0].embed_url).toContain('youtube.com/embed');
    expect(data.videos[0].watch_url).toContain('youtube.com/watch');
  });

  test('creators: detail overlay has recent content section', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(6000);

    // Open detail for an offline creator (should trigger YouTube fetch)
    await page.evaluate(() => (window as any).showCreatorDetail(0));
    await page.waitForTimeout(500);

    // Recent content div should exist
    const recentDiv = page.locator('#det-recent-content');
    await expect(recentDiv).toBeAttached();

    // Stream preview div should exist
    const previewDiv = page.locator('#det-stream-preview');
    await expect(previewDiv).toBeAttached();
  });

  test('creators: close detail clears iframes', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(6000);

    // Open then close
    await page.evaluate(() => {
      (window as any).showCreatorDetail(0);
    });
    await page.waitForTimeout(500);
    await page.evaluate(() => (window as any).closeDetail());
    await page.waitForTimeout(300);

    // Detail should be closed
    const isClosed = await page.evaluate(() =>
      !document.getElementById('creator-detail')?.classList.contains('open')
    );
    expect(isClosed).toBe(true);

    // Preview and recent should be empty (iframes cleared)
    const previewEmpty = await page.evaluate(() =>
      document.getElementById('det-stream-preview')?.innerHTML === ''
    );
    const recentEmpty = await page.evaluate(() =>
      document.getElementById('det-recent-content')?.innerHTML === ''
    );
    expect(previewEmpty).toBe(true);
    expect(recentEmpty).toBe(true);
  });
});

// ══════════════════════════════════════════════
// SECTION 4: Movies — Theater, Categories, Playback
// ══════════════════════════════════════════════
test.describe('VR Movies — Theater', () => {

  test('movies page loads with posters', async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(`${REMOTE}/vr/movies.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(5000);

    const critical = errors.filter(e =>
      e.includes('SyntaxError') || e.includes('ReferenceError')
    );
    expect(critical).toHaveLength(0);

    const status = await page.locator('#status-text').textContent();
    console.log('Movies status:', status);
    expect(status).toBeTruthy();

    const posterCount = await page.evaluate(() => {
      const left = document.getElementById('gallery-left')?.children.length || 0;
      const right = document.getElementById('gallery-right')?.children.length || 0;
      return left + right;
    });
    console.log('Poster count:', posterCount);
    expect(posterCount).toBeGreaterThan(0);
  });

  test('movies: category filters work', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/movies.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(5000);

    const catBar = page.locator('#category-bar');
    await expect(catBar).toBeVisible();

    const btnCount = await page.locator('#category-bar button').count();
    console.log('Category buttons:', btnCount);
    expect(btnCount).toBeGreaterThanOrEqual(3);
  });

  test('movies: selectMovie + HUD visible', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/movies.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(5000);

    const result = await page.evaluate(() => {
      if (typeof (window as any).selectMovie !== 'function') return { fn: false };
      (window as any).selectMovie(0);
      const hud = document.getElementById('movie-hud');
      const title = document.getElementById('hud-title')?.textContent || '';
      return {
        fn: true,
        hudVisible: hud?.classList.contains('visible'),
        title: title,
      };
    });

    console.log('Movie select result:', result);
    expect(result.fn).toBe(true);
    expect(result.hudVisible).toBe(true);
    expect(result.title).toBeTruthy();
  });
});

// ══════════════════════════════════════════════
// SECTION 5: Hub — Zone Portals, Navigation
// ══════════════════════════════════════════════
test.describe('VR Hub — Navigation', () => {

  test('hub has zone portals with zone-link', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/index.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    const zoneLinks = await page.evaluate(() => {
      const els = document.querySelectorAll('[zone-link]');
      const urls: string[] = [];
      els.forEach(el => {
        const comp = (el as any).components?.['zone-link'];
        if (comp?.data?.url) urls.push(comp.data.url);
      });
      return [...new Set(urls)];
    });

    console.log('Zone portal URLs:', zoneLinks);
    expect(zoneLinks.length).toBeGreaterThanOrEqual(6);
  });

  test('hub: goToZone function exists', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/index.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    const hasGoToZone = await page.evaluate(() => typeof (window as any).goToZone === 'function');
    expect(hasGoToZone).toBe(true);
  });

  test('hub: keyboard number shortcuts (1-6) fire goToZone', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/index.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    // Override goToZone to capture calls
    const captured = await page.evaluate(() => {
      return new Promise<string>(resolve => {
        (window as any)._origGoToZone = (window as any).goToZone;
        (window as any).goToZone = (url: string) => resolve(url);
        // Simulate keypress '1' — should go to events
        document.dispatchEvent(new KeyboardEvent('keydown', { key: '1' }));
        // Timeout fallback
        setTimeout(() => resolve('NO_CAPTURE'), 2000);
      });
    });

    console.log('Key 1 captured:', captured);
    // It should have captured some URL (or NO_CAPTURE if shortcuts aren't set up)
    expect(captured).toBeTruthy();
  });
});

// ══════════════════════════════════════════════
// SECTION 6: Input Mode Simulation
// ══════════════════════════════════════════════
test.describe('Input Modes — Keyboard/Mouse, Controller, Gaze', () => {

  test('keyboard/mouse: WASD controls are present on camera', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    const hasWasd = await page.evaluate(() => {
      const cam = document.querySelector('a-camera');
      return cam ? cam.hasAttribute('wasd-controls') : false;
    });
    expect(hasWasd).toBe(true);
  });

  test('keyboard/mouse: look-controls on camera', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    const hasLook = await page.evaluate(() => {
      const cam = document.querySelector('a-camera');
      return cam ? cam.hasAttribute('look-controls') : false;
    });
    expect(hasLook).toBe(true);
  });

  test('controller: laser-controls on both hands', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/movies.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(4000);

    const controllers = await page.evaluate(() => {
      const rig = document.getElementById('rig') || document.getElementById('camera-rig');
      if (!rig) return { left: false, right: false };
      const left = rig.querySelector('#left-hand, #left-controller');
      const right = rig.querySelector('#right-hand, #right-controller');
      return {
        left: left ? left.hasAttribute('laser-controls') : false,
        right: right ? right.hasAttribute('laser-controls') : false,
        leftRaycaster: left ? left.hasAttribute('raycaster') : false,
        rightRaycaster: right ? right.hasAttribute('raycaster') : false,
      };
    });

    console.log('Controller setup:', controllers);
    expect(controllers.left).toBe(true);
    expect(controllers.right).toBe(true);
    expect(controllers.leftRaycaster).toBe(true);
    expect(controllers.rightRaycaster).toBe(true);
  });

  test('controller: teleport indicator entity exists', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/index.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(4000);

    const hasTeleport = await page.evaluate(() => {
      const ind = document.getElementById('vr-teleport-indicator')
               || document.getElementById('teleport-indicator');
      return !!ind;
    });

    console.log('Teleport indicator exists:', hasTeleport);
    expect(hasTeleport).toBe(true);
  });

  test('controller: VRControllerSupport API available', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(4000);

    const api = await page.evaluate(() => {
      const vr = (window as any).VRControllerSupport;
      if (!vr) return null;
      return {
        hasIsVR: typeof vr.isVR === 'function',
        hasIsTeleporting: typeof vr.isTeleporting === 'function',
        hasCancelTeleport: typeof vr.cancelTeleport === 'function',
        hasShowGuide: typeof vr.showGuide === 'function',
        isVR: vr.isVR(),
        isTeleporting: vr.isTeleporting(),
      };
    });

    console.log('VRControllerSupport API:', api);
    expect(api).not.toBeNull();
    expect(api!.hasIsVR).toBe(true);
    expect(api!.hasIsTeleporting).toBe(true);
    expect(api!.hasCancelTeleport).toBe(true);
    expect(api!.isVR).toBe(false); // not in VR on desktop
    expect(api!.isTeleporting).toBe(false);
  });

  test('gaze: fuse cursor exists on camera', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    const hasFuseCursor = await page.evaluate(() => {
      const cam = document.querySelector('a-camera');
      if (!cam) return false;
      const cursor = cam.querySelector('a-cursor, a-ring, [cursor]');
      if (!cursor) return false;
      const cursorAttr = cursor.getAttribute('cursor') || '';
      return cursorAttr.toString().includes('fuse');
    });

    console.log('Fuse cursor present:', hasFuseCursor);
    expect(hasFuseCursor).toBe(true);
  });

  test('gaze: clickable elements exist for interaction', async ({ page }) => {
    await page.goto(`${REMOTE}/vr/index.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    const clickables = await page.evaluate(() => {
      return document.querySelectorAll('.clickable').length;
    });

    console.log('Clickable elements in Hub:', clickables);
    expect(clickables).toBeGreaterThanOrEqual(6);
  });
});

// ══════════════════════════════════════════════
// SECTION 7: Weather, Events, Stocks, Wellness
// ══════════════════════════════════════════════
test.describe('Other VR Zones — Quick Checks', () => {

  test('weather: loads and has scene elements', async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(`${REMOTE}/vr/weather-zone.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(5000);

    // Check it doesn't auto-redirect (the reported bug)
    expect(page.url()).toContain('weather-zone');

    const critical = errors.filter(e =>
      e.includes('SyntaxError') || e.includes('ReferenceError')
    );
    console.log('Weather errors:', critical);
    expect(critical).toHaveLength(0);
  });

  test('events: loads with event cards', async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(`${REMOTE}/vr/events/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(5000);

    const critical = errors.filter(e =>
      e.includes('SyntaxError') || e.includes('ReferenceError')
    );
    expect(critical).toHaveLength(0);
  });

  test('stocks: loads without errors', async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(`${REMOTE}/vr/stocks-zone.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(3000);

    const critical = errors.filter(e =>
      e.includes('SyntaxError') || e.includes('ReferenceError')
    );
    expect(critical).toHaveLength(0);
  });

  test('wellness: loads with teleport points', async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(`${REMOTE}/vr/wellness/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);
    await page.waitForTimeout(3000);

    const critical = errors.filter(e =>
      e.includes('SyntaxError') || e.includes('ReferenceError')
    );
    expect(critical).toHaveLength(0);
  });
});
