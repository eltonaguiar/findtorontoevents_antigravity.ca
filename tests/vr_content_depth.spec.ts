import { test, expect, Page } from '@playwright/test';

/**
 * VR Content Depth & Cross-Zone Intelligence — Set 14 Tests
 *
 * Tests scratchpad, RSVP, genre filter, creator comparison, sector map,
 * weather alerts, breathing, news ticker, cross-zone timeline, ambient lighting.
 */

const BENIGN = ['Unexpected identifier', 'registerMaterial', 'registerShader', 'favicon.ico', 'net::ERR', 'already registered', 'is not defined', 'Haptics', 'webkitSpeechRecognition'];
function benign(msg: string) { return BENIGN.some(k => msg.includes(k)); }

async function jsErrors(page: Page) {
  const errs: string[] = [];
  page.on('pageerror', e => { if (!benign(e.message)) errs.push(e.message); });
  return errs;
}

async function ready(page: Page, url: string) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(3500);
}

/* ── Core Loading ──────────────────────────────── */
test.describe('Set 14 Core Loading', () => {
  test('Hub: VRContentDepth global available', async ({ page }) => {
    const errs = await jsErrors(page);
    await ready(page, '/vr/');
    const has = await page.evaluate(() => typeof (window as any).VRContentDepth === 'object');
    expect(has).toBe(true);
    expect(await page.evaluate(() => (window as any).VRContentDepth.version)).toBe(14);
    expect(errs.length).toBe(0);
  });

  for (const z of [
    { name: 'Events', url: '/vr/events/', zone: 'events' },
    { name: 'Movies', url: '/vr/movies.html', zone: 'movies' },
    { name: 'Creators', url: '/vr/creators.html', zone: 'creators' },
    { name: 'Stocks', url: '/vr/stocks-zone.html', zone: 'stocks' },
    { name: 'Wellness', url: '/vr/wellness/', zone: 'wellness' },
  ]) {
    test(`${z.name}: loaded`, async ({ page }) => {
      const errs = await jsErrors(page);
      await ready(page, z.url);
      expect(await page.evaluate(() => (window as any).VRContentDepth?.zone)).toBe(z.zone);
      expect(errs.length).toBe(0);
    });
  }
});

/* ── 1. Quick Notes Scratchpad ─────────────────── */
test.describe('Scratchpad (#1)', () => {
  test('Toggle creates pad', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRContentDepth.scratchpad.toggle());
    await page.waitForTimeout(300);
    const has = await page.evaluate(() => !!document.getElementById('vr14-scratch'));
    expect(has).toBe(true);
  });

  test('Can set and get text', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRContentDepth.scratchpad.setText('Hello VR'));
    const text = await page.evaluate(() => (window as any).VRContentDepth.scratchpad.getText());
    expect(text).toBe('Hello VR');
  });
});

/* ── 2. Events RSVP ───────────────────────────── */
test.describe('Events RSVP (#2)', () => {
  test('RSVP badge in Events zone', async ({ page }) => {
    await ready(page, '/vr/events/');
    const has = await page.evaluate(() => !!document.getElementById('vr14-rsvp-badge'));
    expect(has).toBe(true);
  });

  test('Can set and get RSVP', async ({ page }) => {
    await ready(page, '/vr/events/');
    await page.evaluate(() => (window as any).VRContentDepth.eventsRSVP.set('evt1', 'attending'));
    const rsvp = await page.evaluate(() => (window as any).VRContentDepth.eventsRSVP.get('evt1'));
    expect(rsvp.status).toBe('attending');
  });

  test('Count works', async ({ page }) => {
    await ready(page, '/vr/events/');
    await page.evaluate(() => {
      (window as any).VRContentDepth.eventsRSVP.set('e1', 'attending');
      (window as any).VRContentDepth.eventsRSVP.set('e2', 'interested');
      (window as any).VRContentDepth.eventsRSVP.set('e3', 'attending');
    });
    const attending = await page.evaluate(() => (window as any).VRContentDepth.eventsRSVP.getCount('attending'));
    expect(attending).toBeGreaterThanOrEqual(2);
  });

  test('Null outside Events', async ({ page }) => {
    await ready(page, '/vr/');
    const v = await page.evaluate(() => (window as any).VRContentDepth.eventsRSVP);
    expect(v).toBeNull();
  });
});

/* ── 3. Movies Genre Filter ────────────────────── */
test.describe('Genre Filter (#3)', () => {
  test('Genre panel in Movies', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    const has = await page.evaluate(() => !!document.getElementById('vr14-genres'));
    expect(has).toBe(true);
  });

  test('Has 9 genre tags', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    const count = await page.evaluate(() => document.querySelectorAll('.vr14-genre-tag').length);
    expect(count).toBe(9);
  });

  test('Can toggle genre', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    await page.evaluate(() => (window as any).VRContentDepth.moviesGenreFilter.toggleGenre('Action'));
    let sel = await page.evaluate(() => (window as any).VRContentDepth.moviesGenreFilter.getSelected());
    expect(sel).toContain('Action');
    await page.evaluate(() => (window as any).VRContentDepth.moviesGenreFilter.toggleGenre('Action'));
    sel = await page.evaluate(() => (window as any).VRContentDepth.moviesGenreFilter.getSelected());
    expect(sel).not.toContain('Action');
  });
});

/* ── 4. Creator Comparison ─────────────────────── */
test.describe('Creator Comparison (#4)', () => {
  test('Available in Creators zone', async ({ page }) => {
    await ready(page, '/vr/creators.html');
    const has = await page.evaluate(() => typeof (window as any).VRContentDepth.creatorComparison?.setSlot === 'function');
    expect(has).toBe(true);
  });

  test('Can set slots and open panel', async ({ page }) => {
    await ready(page, '/vr/creators.html');
    await page.evaluate(() => {
      (window as any).VRContentDepth.creatorComparison.setSlot(0, { name: 'Creator A', followers: '1M', views: '50M', platform: 'Twitch' });
      (window as any).VRContentDepth.creatorComparison.setSlot(1, { name: 'Creator B', followers: '800K', views: '30M', platform: 'YouTube' });
      (window as any).VRContentDepth.creatorComparison.open();
    });
    await page.waitForTimeout(300);
    const has = await page.evaluate(() => !!document.getElementById('vr14-compare'));
    expect(has).toBe(true);
  });
});

/* ── 5. Stocks Sector Map ──────────────────────── */
test.describe('Sector Map (#5)', () => {
  test('Sector chart in Stocks zone', async ({ page }) => {
    await ready(page, '/vr/stocks-zone.html');
    const has = await page.evaluate(() => !!document.getElementById('vr14-sectors'));
    expect(has).toBe(true);
  });

  test('Has 6 sectors', async ({ page }) => {
    await ready(page, '/vr/stocks-zone.html');
    const sectors = await page.evaluate(() => (window as any).VRContentDepth.stocksSectorMap.getSectors());
    expect(sectors.length).toBe(6);
    expect(sectors[0].name).toBe('Technology');
  });
});

/* ── 6. Weather Alerts ─────────────────────────── */
test.describe('Weather Alerts (#6)', () => {
  test('Available in Weather zone', async ({ page }) => {
    await ready(page, '/vr/weather-zone.html');
    const has = await page.evaluate(() => typeof (window as any).VRContentDepth.weatherAlerts?.check === 'function');
    expect(has).toBe(true);
  });

  test('Alerts array accessible', async ({ page }) => {
    await ready(page, '/vr/weather-zone.html');
    const alerts = await page.evaluate(() => (window as any).VRContentDepth.weatherAlerts.getAlerts());
    expect(Array.isArray(alerts)).toBe(true);
  });
});

/* ── 7. Wellness Breathing ─────────────────────── */
test.describe('Breathing Exercise (#7)', () => {
  test('Breathing UI in Wellness zone', async ({ page }) => {
    await ready(page, '/vr/wellness/');
    const has = await page.evaluate(() => !!document.getElementById('vr14-breathe'));
    expect(has).toBe(true);
  });

  test('Can start and stop', async ({ page }) => {
    await ready(page, '/vr/wellness/');
    await page.evaluate(() => (window as any).VRContentDepth.breathingExercise.start());
    let running = await page.evaluate(() => (window as any).VRContentDepth.breathingExercise.isRunning());
    expect(running).toBe(true);
    let phase = await page.evaluate(() => (window as any).VRContentDepth.breathingExercise.getPhase());
    expect(phase).toBe('inhale');
    await page.evaluate(() => (window as any).VRContentDepth.breathingExercise.stop());
    running = await page.evaluate(() => (window as any).VRContentDepth.breathingExercise.isRunning());
    expect(running).toBe(false);
  });
});

/* ── 8. Hub News Ticker ────────────────────────── */
test.describe('News Ticker (#8)', () => {
  test('Ticker in Hub', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr14-ticker'));
    expect(has).toBe(true);
  });

  test('Has headlines', async ({ page }) => {
    await ready(page, '/vr/');
    const h = await page.evaluate(() => (window as any).VRContentDepth.newsTicker.getHeadlines());
    expect(h.length).toBeGreaterThanOrEqual(5);
  });

  test('Null outside Hub', async ({ page }) => {
    await ready(page, '/vr/events/');
    const v = await page.evaluate(() => (window as any).VRContentDepth.newsTicker);
    expect(v).toBeNull();
  });
});

/* ── 9. Cross-Zone Timeline ────────────────────── */
test.describe('Timeline (#9)', () => {
  test('Gather returns array', async ({ page }) => {
    await ready(page, '/vr/');
    const items = await page.evaluate(() => (window as any).VRContentDepth.crossTimeline.gather());
    expect(Array.isArray(items)).toBe(true);
  });

  test('Opens and closes', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRContentDepth.crossTimeline.open());
    await page.waitForTimeout(300);
    let has = await page.evaluate(() => !!document.getElementById('vr14-timeline'));
    expect(has).toBe(true);
    await page.evaluate(() => (window as any).VRContentDepth.crossTimeline.open());
    await page.waitForTimeout(300);
    has = await page.evaluate(() => !!document.getElementById('vr14-timeline'));
    expect(has).toBe(false);
  });
});

/* ── 10. Ambient Lighting Sync ─────────────────── */
test.describe('Ambient Lighting (#10)', () => {
  test('API available', async ({ page }) => {
    await ready(page, '/vr/');
    expect(await page.evaluate(() => typeof (window as any).VRContentDepth.ambientLighting.toggle)).toBe('function');
  });

  test('Enabled by default', async ({ page }) => {
    await ready(page, '/vr/');
    const enabled = await page.evaluate(() => (window as any).VRContentDepth.ambientLighting.isEnabled());
    expect(enabled).toBe(true);
  });

  test('Config matches zone', async ({ page }) => {
    await ready(page, '/vr/events/');
    const config = await page.evaluate(() => (window as any).VRContentDepth.ambientLighting.getConfig());
    expect(config.color).toBe('#ff6b6b');
  });

  test('Overlay element created', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr14-light-overlay'));
    expect(has).toBe(true);
  });
});

/* ── Cross-Zone: No JS errors ────────────────── */
test.describe('No JS errors with Set 14', () => {
  for (const z of [
    { name: 'Hub', url: '/vr/' },
    { name: 'Events', url: '/vr/events/' },
    { name: 'Movies', url: '/vr/movies.html' },
    { name: 'Creators', url: '/vr/creators.html' },
    { name: 'Stocks', url: '/vr/stocks-zone.html' },
    { name: 'Wellness', url: '/vr/wellness/' },
    { name: 'Weather', url: '/vr/weather-zone.html' },
  ]) {
    test(`${z.name}: no critical JS errors`, async ({ page }) => {
      const errs = await jsErrors(page);
      await ready(page, z.url);
      expect(errs.length).toBe(0);
    });
  }
});
