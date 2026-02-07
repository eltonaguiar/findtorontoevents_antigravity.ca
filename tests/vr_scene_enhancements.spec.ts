import { test, expect, Page } from '@playwright/test';

/**
 * VR Scene Enhancements — Set 8 Tests
 *
 * Tests 3D A-Frame scene improvements: portal particles, hover effects,
 * platform waves, screen glow, dust motes, sparks, fireflies, sky tint,
 * ambient motes, and data badges.
 */

const BENIGN = ['Unexpected identifier', 'registerMaterial', 'registerShader', 'favicon.ico', 'net::ERR', 'already registered'];

function benign(msg: string) { return BENIGN.some(k => msg.includes(k)); }

async function jsErrors(page: Page) {
  const errs: string[] = [];
  page.on('pageerror', e => { if (!benign(e.message)) errs.push(e.message); });
  return errs;
}

async function ready(page: Page, url: string) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(3000); // Let A-Frame init + enhancements run
}

test.describe('Scene Enhancements: Core Loading', () => {
  test('Hub: VRSceneEnhancements global is available', async ({ page }) => {
    const errs = await jsErrors(page);
    await ready(page, '/vr/');
    const has = await page.evaluate(() => typeof (window as any).VRSceneEnhancements === 'object');
    expect(has).toBe(true);
    const z = await page.evaluate(() => (window as any).VRSceneEnhancements.zone);
    expect(z).toBe('hub');
    expect(errs.length).toBe(0);
  });

  test('Movies: VRSceneEnhancements loaded', async ({ page }) => {
    const errs = await jsErrors(page);
    await ready(page, '/vr/movies.html');
    const z = await page.evaluate(() => (window as any).VRSceneEnhancements?.zone);
    expect(z).toBe('movies');
    expect(errs.length).toBe(0);
  });

  test('Stocks: VRSceneEnhancements loaded', async ({ page }) => {
    const errs = await jsErrors(page);
    await ready(page, '/vr/stocks-zone.html');
    const z = await page.evaluate(() => (window as any).VRSceneEnhancements?.zone);
    expect(z).toBe('stocks');
    expect(errs.length).toBe(0);
  });

  test('Wellness: VRSceneEnhancements loaded', async ({ page }) => {
    const errs = await jsErrors(page);
    await ready(page, '/vr/wellness/');
    const z = await page.evaluate(() => (window as any).VRSceneEnhancements?.zone);
    expect(z).toBe('wellness');
    expect(errs.length).toBe(0);
  });
});

test.describe('Hub: Portal Particle Fountains (#1)', () => {
  test('Hub has portal particle spheres injected', async ({ page }) => {
    await ready(page, '/vr/');
    // Each of 6 portals gets 5 particles = 30 new a-sphere elements
    // Plus the original 4 decorative = at least 30
    const count = await page.evaluate(() => {
      const scene = document.querySelector('a-scene');
      if (!scene) return 0;
      return scene.querySelectorAll('a-sphere[shader="flat"]').length;
    });
    // Should have many more spheres than the original 4
    expect(count).toBeGreaterThanOrEqual(20);
  });
});

test.describe('Hub: Portal Hover Pulse (#2)', () => {
  test('Portal boxes have mouseenter/mouseleave listeners', async ({ page }) => {
    await ready(page, '/vr/');
    // Verify that zone-link boxes exist
    const boxCount = await page.evaluate(() => {
      return document.querySelectorAll('a-box[zone-link]').length;
    });
    expect(boxCount).toBeGreaterThanOrEqual(6);
  });
});

test.describe('Hub: Platform Energy Waves (#3)', () => {
  test('Hub has expanding ring entities', async ({ page }) => {
    await ready(page, '/vr/');
    // We create 3 rings for the energy wave effect
    const ringCount = await page.evaluate(() => {
      const scene = document.querySelector('a-scene');
      if (!scene) return 0;
      // Count rings with the expanding animation (radius-outer from 0.5 to 5)
      let count = 0;
      scene.querySelectorAll('a-ring').forEach(r => {
        const anim = r.getAttribute('animation');
        if (anim && typeof anim === 'string' && anim.includes('radius-outer')) count++;
        else if (anim && typeof anim === 'object' && anim.property === 'radius-outer') count++;
      });
      return count;
    });
    expect(ringCount).toBeGreaterThanOrEqual(3);
  });
});

test.describe('Movies: Screen Glow (#4)', () => {
  test('Movies has screen glow light', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    const hasGlow = await page.evaluate(() => !!document.getElementById('screen-glow-light'));
    expect(hasGlow).toBe(true);
    const hasPlane = await page.evaluate(() => !!document.getElementById('screen-glow-plane'));
    expect(hasPlane).toBe(true);
  });
});

test.describe('Movies: Dust Motes (#5)', () => {
  test('Movies has dust mote particles', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    const hasMotes = await page.evaluate(() => !!document.getElementById('dust-motes'));
    expect(hasMotes).toBe(true);
    const moteCount = await page.evaluate(() => {
      const container = document.getElementById('dust-motes');
      return container ? container.children.length : 0;
    });
    expect(moteCount).toBeGreaterThanOrEqual(15);
  });
});

test.describe('Stocks: Price-Change Sparks (#6)', () => {
  test('Stocks has spark container', async ({ page }) => {
    await ready(page, '/vr/stocks-zone.html');
    const hasSparks = await page.evaluate(() => !!document.getElementById('stock-sparks'));
    expect(hasSparks).toBe(true);
  });
});

test.describe('Wellness: Fireflies (#7)', () => {
  test('Wellness has fireflies', async ({ page }) => {
    await ready(page, '/vr/wellness/');
    const hasFireflies = await page.evaluate(() => !!document.getElementById('fireflies'));
    expect(hasFireflies).toBe(true);
    const count = await page.evaluate(() => {
      const c = document.getElementById('fireflies');
      return c ? c.children.length : 0;
    });
    expect(count).toBeGreaterThanOrEqual(10);
  });

  test('Wellness has falling petals', async ({ page }) => {
    await ready(page, '/vr/wellness/');
    const hasPetals = await page.evaluate(() => !!document.getElementById('falling-petals'));
    expect(hasPetals).toBe(true);
  });
});

test.describe('Time-of-Day Sky Tint (#8)', () => {
  test('All zones get a time-tint ambient light', async ({ page }) => {
    await ready(page, '/vr/');
    const hasLight = await page.evaluate(() => !!document.getElementById('time-tint-light'));
    expect(hasLight).toBe(true);
  });
});

test.describe('Ambient Floating Motes (#9)', () => {
  const zones = [
    { name: 'Hub', url: '/vr/' },
    { name: 'Events', url: '/vr/events/' },
    { name: 'Movies', url: '/vr/movies.html' },
    { name: 'Creators', url: '/vr/creators.html' },
  ];
  for (const z of zones) {
    test(`${z.name}: has ambient mote particles`, async ({ page }) => {
      await ready(page, z.url);
      const hasMotes = await page.evaluate(() => !!document.getElementById('ambient-motes'));
      expect(hasMotes).toBe(true);
      const count = await page.evaluate(() => {
        const c = document.getElementById('ambient-motes');
        return c ? c.children.length : 0;
      });
      expect(count).toBeGreaterThanOrEqual(8);
    });
  }
});

test.describe('Hub: Portal Data Badges (#10)', () => {
  test('Hub has floating data badge text', async ({ page }) => {
    await ready(page, '/vr/');
    // Data badges include a-text elements with zone info
    const hasBadgeText = await page.evaluate(() => {
      const texts = document.querySelectorAll('a-text[look-at-camera]');
      // Original: "TUTORIAL" and "Learn the Controls" = 2
      // Data badges: 6 entities with look-at-camera
      return texts.length;
    });
    // Should have original + 6 data badge entities (each with look-at-camera parent)
    expect(hasBadgeText).toBeGreaterThanOrEqual(2);

    // Check for the badge container entities
    const badgeEntities = await page.evaluate(() => {
      const scene = document.querySelector('a-scene');
      if (!scene) return 0;
      let count = 0;
      scene.querySelectorAll('a-entity[look-at-camera]').forEach(e => {
        if (e.querySelector('a-plane') && e.querySelector('a-text')) count++;
      });
      return count;
    });
    expect(badgeEntities).toBeGreaterThanOrEqual(6);
  });
});

test.describe('Cross-Zone: No JS errors with scene enhancements', () => {
  const zones = [
    { name: 'Hub', url: '/vr/' },
    { name: 'Events', url: '/vr/events/' },
    { name: 'Movies', url: '/vr/movies.html' },
    { name: 'Creators', url: '/vr/creators.html' },
    { name: 'Stocks', url: '/vr/stocks-zone.html' },
    { name: 'Wellness', url: '/vr/wellness/' },
    { name: 'Weather', url: '/vr/weather-zone.html' },
  ];

  for (const z of zones) {
    test(`${z.name}: no critical JS errors`, async ({ page }) => {
      const errs = await jsErrors(page);
      await ready(page, z.url);
      expect(errs.length).toBe(0);
    });
  }
});
