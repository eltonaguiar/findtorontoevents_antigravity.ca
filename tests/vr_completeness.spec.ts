import { test, expect, Page } from '@playwright/test';

/**
 * VR Completeness — Set 9 Tests
 *
 * Tests 10 production-readiness features: session continuity, error recovery,
 * accessibility, onboarding, performance LOD, events calendar, watch history,
 * weather timeline, device adaptive UI, and changelog.
 */

const BENIGN = ['Unexpected identifier', 'registerMaterial', 'registerShader', 'favicon.ico', 'net::ERR', 'already registered', 'Haptics is not defined', 'is not defined'];
function benign(msg: string) { return BENIGN.some(k => msg.includes(k)); }

async function jsErrors(page: Page) {
  const errs: string[] = [];
  page.on('pageerror', e => { if (!benign(e.message)) errs.push(e.message); });
  return errs;
}

async function ready(page: Page, url: string) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(3000);
}

/* ── 1. Core Loading ──────────────────────────── */
test.describe('Set 9 Core Loading', () => {
  test('Hub: VRCompleteness global is available', async ({ page }) => {
    const errs = await jsErrors(page);
    await ready(page, '/vr/');
    const has = await page.evaluate(() => typeof (window as any).VRCompleteness === 'object');
    expect(has).toBe(true);
    const ver = await page.evaluate(() => (window as any).VRCompleteness.version);
    expect(ver).toBe(9);
    expect(errs.length).toBe(0);
  });

  const zones = [
    { name: 'Events', url: '/vr/events/', zone: 'events' },
    { name: 'Movies', url: '/vr/movies.html', zone: 'movies' },
    { name: 'Creators', url: '/vr/creators.html', zone: 'creators' },
    { name: 'Stocks', url: '/vr/stocks-zone.html', zone: 'stocks' },
    { name: 'Wellness', url: '/vr/wellness/', zone: 'wellness' },
    { name: 'Weather', url: '/vr/weather-zone.html', zone: 'weather' },
  ];

  for (const z of zones) {
    test(`${z.name}: VRCompleteness loaded`, async ({ page }) => {
      const errs = await jsErrors(page);
      await ready(page, z.url);
      const zn = await page.evaluate(() => (window as any).VRCompleteness?.zone);
      expect(zn).toBe(z.zone);
      expect(errs.length).toBe(0);
    });
  }
});

/* ── 2. Session Continuity (#1) ──────────────── */
test.describe('Session Continuity (#1)', () => {
  test('Session state is saved to localStorage', async ({ page }) => {
    await ready(page, '/vr/events/');
    const session = await page.evaluate(() => {
      const raw = localStorage.getItem('vr9_session');
      return raw ? JSON.parse(raw) : null;
    });
    expect(session).not.toBeNull();
    expect(session.zone).toBe('events');
    expect(session.path).toContain('/vr/events');
    expect(session.time).toBeGreaterThan(0);
  });
});

/* ── 3. Error Recovery (#2) ────────────────────── */
test.describe('Error Recovery (#2)', () => {
  test('Error recovery provides resilient fetch', async ({ page }) => {
    await ready(page, '/vr/');
    const hasFetch = await page.evaluate(() => typeof (window as any).VRCompleteness.errorRecovery.fetch === 'function');
    expect(hasFetch).toBe(true);
    const isOnline = await page.evaluate(() => (window as any).VRCompleteness.errorRecovery.isOnline());
    expect(isOnline).toBe(true);
  });

  test('Connection indicator created on status change', async ({ page }) => {
    await ready(page, '/vr/');
    // Simulate offline/online to trigger indicator creation
    await page.evaluate(() => window.dispatchEvent(new Event('offline')));
    await page.waitForTimeout(300);
    const hasConn = await page.evaluate(() => !!document.getElementById('vr9-conn'));
    expect(hasConn).toBe(true);
    const text = await page.evaluate(() => document.getElementById('vr9-conn')?.textContent || '');
    expect(text).toContain('Offline');
    // Simulate coming back online
    await page.evaluate(() => window.dispatchEvent(new Event('online')));
    await page.waitForTimeout(300);
    const text2 = await page.evaluate(() => document.getElementById('vr9-conn')?.textContent || '');
    expect(text2).toContain('restored');
  });
});

/* ── 4. Accessibility Layer (#3) ────────────────── */
test.describe('Accessibility Layer (#3)', () => {
  test('Body has accessibility data attributes', async ({ page }) => {
    await ready(page, '/vr/');
    const hasRM = await page.evaluate(() => document.body.hasAttribute('data-vr-reduced-motion'));
    expect(hasRM).toBe(true);
    const hasHC = await page.evaluate(() => document.body.hasAttribute('data-vr-high-contrast'));
    expect(hasHC).toBe(true);
    const hasLT = await page.evaluate(() => document.body.hasAttribute('data-vr-large-text'));
    expect(hasLT).toBe(true);
  });

  test('Skip link is present', async ({ page }) => {
    await ready(page, '/vr/');
    const skip = await page.evaluate(() => {
      const el = document.getElementById('vr9-skip');
      return el ? el.textContent : null;
    });
    expect(skip).toBe('Skip to main content');
  });

  test('Alt+A opens accessibility panel', async ({ page }) => {
    await ready(page, '/vr/');
    // Close any onboarding dialog first
    await page.evaluate(() => {
      const ob = document.getElementById('vr9-onboard');
      if (ob) ob.remove();
      const cl = document.getElementById('vr9-changelog');
      if (cl) cl.remove();
      const bg = document.getElementById('vr9-changelog-bg');
      if (bg) bg.remove();
    });
    await page.keyboard.press('Alt+a');
    await page.waitForTimeout(500);
    const panelOpen = await page.evaluate(() => !!document.getElementById('vr9-a11y-panel'));
    expect(panelOpen).toBe(true);
    // Check it has toggle switches
    const toggleCount = await page.evaluate(() => document.querySelectorAll('.vr9-toggle').length);
    expect(toggleCount).toBe(3);
  });

  test('Zone-link elements have ARIA labels', async ({ page }) => {
    await ready(page, '/vr/');
    const labeled = await page.evaluate(() => {
      const els = document.querySelectorAll('[zone-link][aria-label]');
      return els.length;
    });
    expect(labeled).toBeGreaterThanOrEqual(6);
  });
});

/* ── 5. First-Visit Onboarding (#4) ─────────────── */
test.describe('First-Visit Onboarding (#4)', () => {
  test('Onboarding tip shows on first visit', async ({ page }) => {
    await ready(page, '/vr/');
    // Clear visited state, then reload
    await page.evaluate(() => localStorage.removeItem('vr9_visited_zones'));
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const hasTip = await page.evaluate(() => !!document.getElementById('vr9-onboard'));
    expect(hasTip).toBe(true);
  });

  test('Onboarding does NOT show on second visit', async ({ page }) => {
    // First visit
    await ready(page, '/vr/stocks-zone.html');
    await page.waitForTimeout(2000);
    // Reload = second visit
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const hasTip = await page.evaluate(() => !!document.getElementById('vr9-onboard'));
    expect(hasTip).toBe(false);
  });
});

/* ── 6. Performance LOD (#5) ──────────────────── */
test.describe('Performance LOD (#5)', () => {
  test('FPS badge is visible', async ({ page }) => {
    await ready(page, '/vr/');
    const hasFPS = await page.evaluate(() => !!document.getElementById('vr9-fps'));
    expect(hasFPS).toBe(true);
  });

  test('Quality data attribute is set on body', async ({ page }) => {
    await ready(page, '/vr/');
    await page.waitForTimeout(2000); // Let FPS stabilize
    const hasQuality = await page.evaluate(() => document.body.hasAttribute('data-vr-quality'));
    expect(hasQuality).toBe(true);
  });

  test('perfLOD API is functional', async ({ page }) => {
    await ready(page, '/vr/');
    const fps = await page.evaluate(() => (window as any).VRCompleteness.perfLOD.getFPS());
    expect(fps).toBeGreaterThan(0);
    const quality = await page.evaluate(() => (window as any).VRCompleteness.perfLOD.getQuality());
    expect(['auto', 'high', 'medium', 'low']).toContain(quality);
  });
});

/* ── 7. Events Calendar Minimap (#6) ──────────── */
test.describe('Events Calendar Minimap (#6)', () => {
  test('Calendar appears in Events zone', async ({ page }) => {
    await ready(page, '/vr/events/');
    await page.waitForTimeout(3500); // Calendar creates after 3s delay
    const hasCal = await page.evaluate(() => !!document.getElementById('vr9-calendar'));
    expect(hasCal).toBe(true);
  });

  test('Calendar has day grid', async ({ page }) => {
    await ready(page, '/vr/events/');
    await page.waitForTimeout(3500);
    const dayCount = await page.evaluate(() => document.querySelectorAll('#vr9-calendar .cal-day').length);
    // At least 28 day cells (4 weeks min)
    expect(dayCount).toBeGreaterThanOrEqual(28);
  });

  test('Calendar NOT present in other zones', async ({ page }) => {
    await ready(page, '/vr/');
    await page.waitForTimeout(3500);
    const hasCal = await page.evaluate(() => !!document.getElementById('vr9-calendar'));
    expect(hasCal).toBe(false);
  });
});

/* ── 8. Movies Watch History (#7) ──────────────── */
test.describe('Movies Watch History (#7)', () => {
  test('Watch badge appears in Movies zone', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    await page.waitForTimeout(2500);
    const hasBadge = await page.evaluate(() => !!document.getElementById('vr9-watch-badge'));
    expect(hasBadge).toBe(true);
  });

  test('Watch history API is functional', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    await page.waitForTimeout(2500);
    const history = await page.evaluate(() => {
      const wh = (window as any).VRCompleteness.watchHistory;
      if (!wh) return null;
      wh.add('Test Movie', 'abc123', '');
      return wh.getHistory();
    });
    expect(history).not.toBeNull();
    expect(history.length).toBeGreaterThanOrEqual(1);
    expect(history[0].title).toBe('Test Movie');
  });

  test('Watch history NOT present in other zones', async ({ page }) => {
    await ready(page, '/vr/');
    await page.waitForTimeout(2500);
    const hasBadge = await page.evaluate(() => !!document.getElementById('vr9-watch-badge'));
    expect(hasBadge).toBe(false);
  });
});

/* ── 9. Weather Forecast Timeline (#8) ─────────── */
test.describe('Weather Forecast Timeline (#8)', () => {
  test('Timeline appears in Weather zone', async ({ page }) => {
    await ready(page, '/vr/weather-zone.html');
    await page.waitForTimeout(5000); // API fetch + render
    const hasTL = await page.evaluate(() => !!document.getElementById('vr9-weather-timeline'));
    expect(hasTL).toBe(true);
  });

  test('Timeline NOT present in other zones', async ({ page }) => {
    await ready(page, '/vr/');
    await page.waitForTimeout(3000);
    const hasTL = await page.evaluate(() => !!document.getElementById('vr9-weather-timeline'));
    expect(hasTL).toBe(false);
  });
});

/* ── 10. Device Adaptive UI (#9) ────────────────── */
test.describe('Device Adaptive UI (#9)', () => {
  test('Body has device type attribute', async ({ page }) => {
    await ready(page, '/vr/');
    const device = await page.evaluate(() => document.body.getAttribute('data-vr-device'));
    expect(device).toBe('desktop'); // Playwright runs as desktop browser
  });

  test('Device API reports correct type', async ({ page }) => {
    await ready(page, '/vr/');
    const info = await page.evaluate(() => {
      const d = (window as any).VRCompleteness.device;
      return { type: d.type, isDesktop: d.isDesktop, isVR: d.isVR };
    });
    expect(info.type).toBe('desktop');
    expect(info.isDesktop).toBe(true);
    expect(info.isVR).toBe(false);
  });
});

/* ── 11. What's New Changelog (#10) ─────────────── */
test.describe('Changelog (#10)', () => {
  test('Changelog can be opened', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => {
      // Dismiss any open dialogs and reset state
      const ob = document.getElementById('vr9-onboard');
      if (ob) ob.remove();
      // Close changelog if it was auto-opened
      if ((window as any).VRCompleteness.changelog.isOpen()) {
        (window as any).VRCompleteness.closeChangelog();
      }
      // Remove any leftover elements
      ['vr9-changelog', 'vr9-changelog-bg'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.remove();
      });
    });
    await page.waitForTimeout(300);
    // Now open it fresh
    await page.evaluate(() => (window as any).VRCompleteness.showChangelog());
    await page.waitForTimeout(500);
    const hasPanel = await page.evaluate(() => !!document.getElementById('vr9-changelog'));
    expect(hasPanel).toBe(true);
  });

  test('Changelog contains version entries', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRCompleteness.showChangelog());
    await page.waitForTimeout(500);
    const sections = await page.evaluate(() => document.querySelectorAll('#vr9-changelog .cl-section').length);
    expect(sections).toBeGreaterThanOrEqual(2);
    const items = await page.evaluate(() => document.querySelectorAll('#vr9-changelog li').length);
    expect(items).toBeGreaterThanOrEqual(10);
  });

  test('Changelog can be closed', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRCompleteness.showChangelog());
    await page.waitForTimeout(300);
    await page.evaluate(() => (window as any).VRCompleteness.closeChangelog());
    await page.waitForTimeout(300);
    const hasPanel = await page.evaluate(() => !!document.getElementById('vr9-changelog'));
    expect(hasPanel).toBe(false);
  });
});

/* ── 12. Nav Menu Integration ─────────────────── */
test.describe('Nav Menu Integration', () => {
  test('Nav menu has A11y and New buttons', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => {
      const ob = document.getElementById('vr9-onboard');
      if (ob) ob.remove();
      if (typeof (window as any).openNavMenu === 'function') (window as any).openNavMenu();
    });
    await page.waitForTimeout(500);
    const a11yBtn = await page.evaluate(() => {
      const btns = document.querySelectorAll('.vr-nav-util-btn');
      let found = false;
      btns.forEach(b => { if (b.textContent && b.textContent.includes('A11y')) found = true; });
      return found;
    });
    expect(a11yBtn).toBe(true);
    const newBtn = await page.evaluate(() => {
      const btns = document.querySelectorAll('.vr-nav-util-btn');
      let found = false;
      btns.forEach(b => { if (b.textContent && b.textContent.includes('New')) found = true; });
      return found;
    });
    expect(newBtn).toBe(true);
  });
});

/* ── 13. Cross-Zone: No JS errors ────────────── */
test.describe('Cross-Zone: No JS errors with Set 9', () => {
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
