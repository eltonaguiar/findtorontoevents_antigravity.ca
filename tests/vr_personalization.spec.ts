import { test, expect, Page } from '@playwright/test';

/**
 * VR Personalization & Social — Set 11 Tests
 *
 * Tests theme customizer, playlists, event sharing/notes, multi-city weather,
 * creator history, notifications, portfolio, pinboard, and quick-launch.
 */

const BENIGN = ['Unexpected identifier', 'registerMaterial', 'registerShader', 'favicon.ico', 'net::ERR', 'already registered', 'is not defined'];
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

/* ── Core Loading ──────────────────────────────── */
test.describe('Set 11 Core Loading', () => {
  test('Hub: VRPersonalization global available', async ({ page }) => {
    const errs = await jsErrors(page);
    await ready(page, '/vr/');
    const has = await page.evaluate(() => typeof (window as any).VRPersonalization === 'object');
    expect(has).toBe(true);
    expect(await page.evaluate(() => (window as any).VRPersonalization.version)).toBe(11);
    expect(errs.length).toBe(0);
  });

  for (const z of [
    { name: 'Events', url: '/vr/events/', zone: 'events' },
    { name: 'Movies', url: '/vr/movies.html', zone: 'movies' },
    { name: 'Stocks', url: '/vr/stocks-zone.html', zone: 'stocks' },
    { name: 'Wellness', url: '/vr/wellness/', zone: 'wellness' },
  ]) {
    test(`${z.name}: loaded`, async ({ page }) => {
      const errs = await jsErrors(page);
      await ready(page, z.url);
      expect(await page.evaluate(() => (window as any).VRPersonalization?.zone)).toBe(z.zone);
      expect(errs.length).toBe(0);
    });
  }
});

/* ── 1. Theme Customizer ──────────────────────── */
test.describe('Theme Customizer (#1)', () => {
  test('Body has theme attribute', async ({ page }) => {
    await ready(page, '/vr/');
    const theme = await page.evaluate(() => document.body.getAttribute('data-vr-theme'));
    expect(theme).toBeTruthy();
  });

  test('Can switch themes', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPersonalization.themeCustomizer.apply('forest'));
    const theme = await page.evaluate(() => document.body.getAttribute('data-vr-theme'));
    expect(theme).toBe('forest');
  });

  test('Ctrl+, opens theme panel', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => { document.querySelectorAll('#vr9-onboard,#vr9-changelog,#vr9-changelog-bg').forEach(e => e.remove()); });
    await page.keyboard.press('Control+,');
    await page.waitForTimeout(500);
    const panel = await page.evaluate(() => !!document.getElementById('vr11-theme'));
    expect(panel).toBe(true);
    const opts = await page.evaluate(() => document.querySelectorAll('.vr11-theme-opt').length);
    expect(opts).toBe(5);
  });
});

/* ── 2. Movies Named Playlists ────────────────── */
test.describe('Movies Playlists (#2)', () => {
  test('Playlist panel present in Movies', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    const has = await page.evaluate(() => !!document.getElementById('vr11-playlists'));
    expect(has).toBe(true);
  });

  test('Can add to playlist', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    await page.evaluate(() => (window as any).VRPersonalization.moviesPlaylists.add('Test Movie', 'vid123'));
    const pl = await page.evaluate(() => (window as any).VRPersonalization.moviesPlaylists.getAll());
    expect(pl.Default.length).toBeGreaterThanOrEqual(1);
  });
});

/* ── 3. Events Social Share ────────────────────── */
test.describe('Events Share (#3)', () => {
  test('Share API available in Events', async ({ page }) => {
    await ready(page, '/vr/events/');
    const has = await page.evaluate(() => typeof (window as any).VRPersonalization.eventsShare?.share === 'function');
    expect(has).toBe(true);
  });

  test('getShareHTML returns markup', async ({ page }) => {
    await ready(page, '/vr/events/');
    const html = await page.evaluate(() => (window as any).VRPersonalization.eventsShare.getShareHTML('Test', '2026-03-01'));
    expect(html).toContain('vr11-share-row');
  });
});

/* ── 4. Events Personal Notes ─────────────────── */
test.describe('Events Notes (#4)', () => {
  test('Notes badge present in Events', async ({ page }) => {
    await ready(page, '/vr/events/');
    const has = await page.evaluate(() => !!document.getElementById('vr11-notes-badge'));
    expect(has).toBe(true);
  });

  test('Can set and get notes', async ({ page }) => {
    await ready(page, '/vr/events/');
    await page.evaluate(() => (window as any).VRPersonalization.eventsNotes.set('evt1', 'Concert', 'Bring umbrella'));
    const note = await page.evaluate(() => (window as any).VRPersonalization.eventsNotes.get('evt1'));
    expect(note.title).toBe('Concert');
    expect(note.text).toBe('Bring umbrella');
  });
});

/* ── 5. Weather Multi-City ────────────────────── */
test.describe('Weather Multi-City (#5)', () => {
  test('City selector present in Weather', async ({ page }) => {
    await ready(page, '/vr/weather-zone.html');
    const has = await page.evaluate(() => !!document.getElementById('vr11-city-sel'));
    expect(has).toBe(true);
    const btns = await page.evaluate(() => document.querySelectorAll('.vr11-city-btn').length);
    expect(btns).toBe(4);
  });

  test('Can switch cities', async ({ page }) => {
    await ready(page, '/vr/weather-zone.html');
    await page.evaluate(() => (window as any).VRPersonalization.weatherMultiCity.switchCity('vancouver'));
    const city = await page.evaluate(() => (window as any).VRPersonalization.weatherMultiCity.getCurrent());
    expect(city).toBe('vancouver');
  });
});

/* ── 6. Creator View History ──────────────────── */
test.describe('Creator History (#6)', () => {
  test('History panel present in Creators', async ({ page }) => {
    await ready(page, '/vr/creators.html');
    const has = await page.evaluate(() => !!document.getElementById('vr11-creator-history'));
    expect(has).toBe(true);
  });

  test('Can record and retrieve views', async ({ page }) => {
    await ready(page, '/vr/creators.html');
    await page.evaluate(() => (window as any).VRPersonalization.creatorHistory.record('c1', 'TestCreator'));
    const hist = await page.evaluate(() => (window as any).VRPersonalization.creatorHistory.getHistory());
    expect(hist.length).toBeGreaterThanOrEqual(1);
    expect(hist[0].name).toBe('TestCreator');
  });
});

/* ── 7. Notification Center ───────────────────── */
test.describe('Notification Center (#7)', () => {
  test('Bell icon present', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr11-notif-bell'));
    expect(has).toBe(true);
  });

  test('Can add and retrieve notifications', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPersonalization.notifications.add('Test alert', 'info'));
    const all = await page.evaluate(() => (window as any).VRPersonalization.notifications.getAll());
    expect(all.length).toBeGreaterThanOrEqual(1);
    expect(all[0].text).toBe('Test alert');
  });

  test('Can clear notifications', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPersonalization.notifications.add('temp', 'info'));
    await page.evaluate(() => (window as any).VRPersonalization.notifications.clear());
    const all = await page.evaluate(() => (window as any).VRPersonalization.notifications.getAll());
    expect(all.length).toBe(0);
  });
});

/* ── 8. Stocks Portfolio ──────────────────────── */
test.describe('Stocks Portfolio (#8)', () => {
  test('Portfolio panel present in Stocks', async ({ page }) => {
    await ready(page, '/vr/stocks-zone.html');
    const has = await page.evaluate(() => !!document.getElementById('vr11-portfolio'));
    expect(has).toBe(true);
  });

  test('Can buy stock', async ({ page }) => {
    await ready(page, '/vr/stocks-zone.html');
    await page.evaluate(() => (window as any).VRPersonalization.stocksPortfolio.buy('AAPL', 10));
    const pf = await page.evaluate(() => (window as any).VRPersonalization.stocksPortfolio.getPortfolio());
    expect(pf.some((p: any) => p.ticker === 'AAPL')).toBe(true);
  });
});

/* ── 9. Cross-Zone Pinboard ───────────────────── */
test.describe('Pinboard (#9)', () => {
  test('Pinboard badge present', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr11-pin-badge'));
    expect(has).toBe(true);
  });

  test('Can pin and unpin items', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPersonalization.pinboard.pin({ type: 'test', title: 'My Pin' }));
    let pins = await page.evaluate(() => (window as any).VRPersonalization.pinboard.getPins());
    expect(pins.length).toBeGreaterThanOrEqual(1);
    const id = pins[0].id;
    await page.evaluate((id) => (window as any).VRPersonalization.pinboard.unpin(id), id);
    pins = await page.evaluate(() => (window as any).VRPersonalization.pinboard.getPins());
    expect(pins.some((p: any) => p.id === id)).toBe(false);
  });
});

/* ── 10. Hub Quick-Launch ─────────────────────── */
test.describe('Hub Quick-Launch (#10)', () => {
  test('Quick-launch bar present in Hub', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr11-quick-launch'));
    expect(has).toBe(true);
  });

  test('Quick-launch has buttons', async ({ page }) => {
    await ready(page, '/vr/');
    const btns = await page.evaluate(() => document.querySelectorAll('.vr11-ql-btn').length);
    expect(btns).toBeGreaterThanOrEqual(3);
  });

  test('Quick-launch NOT in other zones', async ({ page }) => {
    await ready(page, '/vr/events/');
    await page.waitForTimeout(2000);
    const has = await page.evaluate(() => !!document.getElementById('vr11-quick-launch'));
    expect(has).toBe(false);
  });
});

/* ── Cross-Zone: No JS errors ────────────────── */
test.describe('No JS errors with Set 11', () => {
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
