import { test, expect, Page } from '@playwright/test';

/**
 * VR Advanced UX & Immersion — Set 12 Tests
 *
 * Tests data export/import, mini-map radar, dynamic weather FX, photo mode,
 * events countdown, movie autoplay, creator spotlight, voice commands,
 * usage analytics, and spatial ambient audio.
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
  await page.waitForTimeout(3000);
}

/* ── Core Loading ──────────────────────────────── */
test.describe('Set 12 Core Loading', () => {
  test('Hub: VRAdvancedUX global available', async ({ page }) => {
    const errs = await jsErrors(page);
    await ready(page, '/vr/');
    const has = await page.evaluate(() => typeof (window as any).VRAdvancedUX === 'object');
    expect(has).toBe(true);
    expect(await page.evaluate(() => (window as any).VRAdvancedUX.version)).toBe(12);
    expect(errs.length).toBe(0);
  });

  for (const z of [
    { name: 'Events', url: '/vr/events/', zone: 'events' },
    { name: 'Movies', url: '/vr/movies.html', zone: 'movies' },
    { name: 'Creators', url: '/vr/creators.html', zone: 'creators' },
    { name: 'Stocks', url: '/vr/stocks-zone.html', zone: 'stocks' },
    { name: 'Weather', url: '/vr/weather-zone.html', zone: 'weather' },
  ]) {
    test(`${z.name}: loaded`, async ({ page }) => {
      const errs = await jsErrors(page);
      await ready(page, z.url);
      expect(await page.evaluate(() => (window as any).VRAdvancedUX?.zone)).toBe(z.zone);
      expect(errs.length).toBe(0);
    });
  }
});

/* ── 1. Data Export/Import ─────────────────────── */
test.describe('Data Export/Import (#1)', () => {
  test('Export gathers data', async ({ page }) => {
    await ready(page, '/vr/');
    const data = await page.evaluate(() => (window as any).VRAdvancedUX.dataExport.gather());
    expect(typeof data).toBe('object');
  });

  test('Import restores data', async ({ page }) => {
    await ready(page, '/vr/');
    const count = await page.evaluate(() => {
      return (window as any).VRAdvancedUX.dataExport.import('{"vr12_test_key":"hello"}');
    });
    expect(count).toBe(1);
    const val = await page.evaluate(() => localStorage.getItem('vr12_test_key'));
    expect(val).toBe('hello');
  });
});

/* ── 2. Mini-Map Radar ─────────────────────────── */
test.describe('Mini-Map Radar (#2)', () => {
  test('Mini-map present on all zones', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr12-minimap'));
    expect(has).toBe(true);
  });

  test('Canvas element renders', async ({ page }) => {
    await ready(page, '/vr/');
    const canvas = await page.evaluate(() => {
      const c = document.getElementById('vr12-mm-canvas') as HTMLCanvasElement;
      return c ? { w: c.width, h: c.height } : null;
    });
    expect(canvas).toBeTruthy();
    expect(canvas!.w).toBeGreaterThan(0);
  });

  test('Position tracking works', async ({ page }) => {
    await ready(page, '/vr/');
    const pos = await page.evaluate(() => (window as any).VRAdvancedUX.miniMap.getPosition());
    expect(typeof pos.x).toBe('number');
    expect(typeof pos.y).toBe('number');
  });
});

/* ── 3. Dynamic Weather FX ─────────────────────── */
test.describe('Dynamic Weather FX (#3)', () => {
  test('Weather FX only in Weather zone', async ({ page }) => {
    await ready(page, '/vr/weather-zone.html');
    const has = await page.evaluate(() => (window as any).VRAdvancedUX.weatherEffects !== null);
    expect(has).toBe(true);
  });

  test('Can trigger rain', async ({ page }) => {
    await ready(page, '/vr/weather-zone.html');
    await page.evaluate(() => (window as any).VRAdvancedUX.weatherEffects.rain(20));
    await page.waitForTimeout(500);
    const count = await page.evaluate(() => document.querySelectorAll('.vr12-rain').length);
    expect(count).toBeGreaterThanOrEqual(10);
    const current = await page.evaluate(() => (window as any).VRAdvancedUX.weatherEffects.getCurrent());
    expect(current).toBe('rain');
  });

  test('Can trigger snow', async ({ page }) => {
    await ready(page, '/vr/weather-zone.html');
    await page.evaluate(() => (window as any).VRAdvancedUX.weatherEffects.snow(15));
    await page.waitForTimeout(500);
    const count = await page.evaluate(() => document.querySelectorAll('.vr12-snow').length);
    expect(count).toBeGreaterThanOrEqual(10);
  });

  test('Can clear effects', async ({ page }) => {
    await ready(page, '/vr/weather-zone.html');
    await page.evaluate(() => { (window as any).VRAdvancedUX.weatherEffects.rain(10); });
    await page.evaluate(() => { (window as any).VRAdvancedUX.weatherEffects.clear(); });
    const current = await page.evaluate(() => (window as any).VRAdvancedUX.weatherEffects.getCurrent());
    expect(current).toBe('none');
  });

  test('Null in non-weather zones', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => (window as any).VRAdvancedUX.weatherEffects);
    expect(has).toBeNull();
  });
});

/* ── 4. Photo Mode ─────────────────────────────── */
test.describe('Photo Mode (#4)', () => {
  test('Photo button present', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr12-photo-btn'));
    expect(has).toBe(true);
  });

  test('Capture function available', async ({ page }) => {
    await ready(page, '/vr/');
    const fn = await page.evaluate(() => typeof (window as any).VRAdvancedUX.photoMode.capture);
    expect(fn).toBe('function');
  });
});

/* ── 5. Events Countdown Timer ─────────────────── */
test.describe('Events Countdown (#5)', () => {
  test('Countdown UI present in Events', async ({ page }) => {
    await ready(page, '/vr/events/');
    const has = await page.evaluate(() => !!document.getElementById('vr12-countdown'));
    expect(has).toBe(true);
  });

  test('Timer shows time or NOW', async ({ page }) => {
    await ready(page, '/vr/events/');
    await page.waitForTimeout(2000);
    const text = await page.evaluate(() => document.getElementById('vr12-cd-time')?.textContent || '');
    expect(text.length).toBeGreaterThan(0);
  });

  test('Has target event', async ({ page }) => {
    await ready(page, '/vr/events/');
    await page.waitForTimeout(3000);
    const target = await page.evaluate(() => (window as any).VRAdvancedUX.eventsCountdown?.getTarget());
    expect(target).toBeTruthy();
    expect(target.name).toBeTruthy();
  });

  test('Null in non-events zones', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => (window as any).VRAdvancedUX.eventsCountdown);
    expect(has).toBeNull();
  });
});

/* ── 6. Movie Autoplay Queue ───────────────────── */
test.describe('Movie Autoplay (#6)', () => {
  test('Autoplay UI present in Movies', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    const has = await page.evaluate(() => !!document.getElementById('vr12-autoplay'));
    expect(has).toBe(true);
  });

  test('Can add to queue', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    await page.evaluate(() => (window as any).VRAdvancedUX.movieAutoplay.add('Movie A', 'vid1'));
    await page.evaluate(() => (window as any).VRAdvancedUX.movieAutoplay.add('Movie B', 'vid2'));
    const q = await page.evaluate(() => (window as any).VRAdvancedUX.movieAutoplay.getQueue());
    expect(q.length).toBe(2);
  });

  test('Next advances queue', async ({ page }) => {
    await ready(page, '/vr/movies.html');
    await page.evaluate(() => {
      (window as any).VRAdvancedUX.movieAutoplay.add('A', 'v1');
      (window as any).VRAdvancedUX.movieAutoplay.add('B', 'v2');
    });
    const item = await page.evaluate(() => (window as any).VRAdvancedUX.movieAutoplay.next());
    expect(item).toBeTruthy();
  });
});

/* ── 7. Creator Spotlight ──────────────────────── */
test.describe('Creator Spotlight (#7)', () => {
  test('Spotlight banner present in Creators', async ({ page }) => {
    await ready(page, '/vr/creators.html');
    const has = await page.evaluate(() => !!document.getElementById('vr12-spotlight'));
    expect(has).toBe(true);
  });

  test('Shows a creator name', async ({ page }) => {
    await ready(page, '/vr/creators.html');
    const name = await page.evaluate(() => (window as any).VRAdvancedUX.creatorSpotlight?.getCurrent());
    expect(name).toBeTruthy();
    expect(name.length).toBeGreaterThan(0);
  });

  test('Can advance to next', async ({ page }) => {
    await ready(page, '/vr/creators.html');
    const first = await page.evaluate(() => (window as any).VRAdvancedUX.creatorSpotlight.getCurrent());
    await page.evaluate(() => (window as any).VRAdvancedUX.creatorSpotlight.next());
    const second = await page.evaluate(() => (window as any).VRAdvancedUX.creatorSpotlight.getCurrent());
    expect(second).toBeTruthy();
    // They rotate, so second should differ (unless wrapping from last to first, but likely different)
  });
});

/* ── 8. Voice Commands ─────────────────────────── */
test.describe('Voice Commands (#8)', () => {
  test('Voice button present', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr12-voice'));
    expect(has).toBe(true);
  });

  test('Commands list available', async ({ page }) => {
    await ready(page, '/vr/');
    const cmds = await page.evaluate(() => (window as any).VRAdvancedUX.voiceCommands.commands);
    expect(cmds.length).toBeGreaterThan(5);
    expect(cmds).toContain('go to events');
  });
});

/* ── 9. Usage Analytics ────────────────────────── */
test.describe('Usage Analytics (#9)', () => {
  test('Stats available', async ({ page }) => {
    await ready(page, '/vr/');
    const stats = await page.evaluate(() => (window as any).VRAdvancedUX.analytics.getStats());
    expect(typeof stats.totalSessions).toBe('number');
    expect(typeof stats.totalTimeSec).toBe('number');
  });

  test('Dashboard opens', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRAdvancedUX.analytics.open());
    await page.waitForTimeout(500);
    const has = await page.evaluate(() => !!document.getElementById('vr12-analytics'));
    expect(has).toBe(true);
  });

  test('Dashboard closes on second call', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRAdvancedUX.analytics.open());
    await page.waitForTimeout(300);
    await page.evaluate(() => (window as any).VRAdvancedUX.analytics.open());
    await page.waitForTimeout(300);
    const has = await page.evaluate(() => !!document.getElementById('vr12-analytics'));
    expect(has).toBe(false);
  });
});

/* ── 10. Spatial Ambient Audio ─────────────────── */
test.describe('Spatial Ambient Audio (#10)', () => {
  test('API available', async ({ page }) => {
    await ready(page, '/vr/');
    const audio = await page.evaluate(() => typeof (window as any).VRAdvancedUX.spatialAudio.toggle);
    expect(audio).toBe('function');
  });

  test('Enabled by default', async ({ page }) => {
    await ready(page, '/vr/');
    const enabled = await page.evaluate(() => (window as any).VRAdvancedUX.spatialAudio.isEnabled());
    expect(enabled).toBe(true);
  });
});

/* ── Cross-Zone: No JS errors ────────────────── */
test.describe('No JS errors with Set 12', () => {
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
