import { test, expect, Page } from '@playwright/test';

/**
 * VR Comfort, Accessibility & Intelligence — Set 13 Tests
 *
 * Tests i18n, zen mode, recommendations, custom hotkeys, transitions,
 * daily challenges, comfort settings, bookmarks, session replay, particle density.
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
test.describe('Set 13 Core Loading', () => {
  test('Hub: VRComfortIntel global available', async ({ page }) => {
    const errs = await jsErrors(page);
    await ready(page, '/vr/');
    const has = await page.evaluate(() => typeof (window as any).VRComfortIntel === 'object');
    expect(has).toBe(true);
    expect(await page.evaluate(() => (window as any).VRComfortIntel.version)).toBe(13);
    expect(errs.length).toBe(0);
  });

  for (const z of [
    { name: 'Events', url: '/vr/events/', zone: 'events' },
    { name: 'Movies', url: '/vr/movies.html', zone: 'movies' },
    { name: 'Stocks', url: '/vr/stocks-zone.html', zone: 'stocks' },
    { name: 'Weather', url: '/vr/weather-zone.html', zone: 'weather' },
  ]) {
    test(`${z.name}: loaded`, async ({ page }) => {
      const errs = await jsErrors(page);
      await ready(page, z.url);
      expect(await page.evaluate(() => (window as any).VRComfortIntel?.zone)).toBe(z.zone);
      expect(errs.length).toBe(0);
    });
  }
});

/* ── 1. Multi-Language i18n ────────────────────── */
test.describe('i18n (#1)', () => {
  test('Language selector present', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr13-lang'));
    expect(has).toBe(true);
    const btns = await page.evaluate(() => document.querySelectorAll('.vr13-lang-btn').length);
    expect(btns).toBe(3);
  });

  test('Can switch to French', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRComfortIntel.i18n.setLang('fr'));
    const lang = await page.evaluate(() => (window as any).VRComfortIntel.i18n.getLang());
    expect(lang).toBe('fr');
    const t = await page.evaluate(() => (window as any).VRComfortIntel.i18n.t('events'));
    expect(t).toBe('Événements');
  });

  test('Can switch to Spanish', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRComfortIntel.i18n.setLang('es'));
    const t = await page.evaluate(() => (window as any).VRComfortIntel.i18n.t('movies'));
    expect(t).toBe('Películas');
  });

  test('Fallback to English for unknown key', async ({ page }) => {
    await ready(page, '/vr/');
    const t = await page.evaluate(() => (window as any).VRComfortIntel.i18n.t('nonexistent'));
    expect(t).toBe('nonexistent');
  });
});

/* ── 2. Zen Mode ───────────────────────────────── */
test.describe('Zen Mode (#2)', () => {
  test('Starts inactive', async ({ page }) => {
    await ready(page, '/vr/');
    const active = await page.evaluate(() => (window as any).VRComfortIntel.zenMode.isActive());
    expect(active).toBe(false);
  });

  test('Can toggle on and off', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRComfortIntel.zenMode.toggle());
    let active = await page.evaluate(() => (window as any).VRComfortIntel.zenMode.isActive());
    expect(active).toBe(true);
    // Zen badge should be visible
    const badge = await page.evaluate(() => {
      const b = document.getElementById('vr13-zen-badge');
      return b ? b.style.display : 'missing';
    });
    expect(badge).toBe('block');
    // Toggle off
    await page.evaluate(() => (window as any).VRComfortIntel.zenMode.toggle());
    active = await page.evaluate(() => (window as any).VRComfortIntel.zenMode.isActive());
    expect(active).toBe(false);
  });
});

/* ── 3. Smart Recommendations ──────────────────── */
test.describe('Recommendations (#3)', () => {
  test('Widget present', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr13-recs'));
    expect(has).toBe(true);
  });

  test('Returns 3 recommendations', async ({ page }) => {
    await ready(page, '/vr/');
    const recs = await page.evaluate(() => (window as any).VRComfortIntel.recommendations.get());
    expect(recs.length).toBe(3);
    expect(recs[0].zone).toBeTruthy();
    expect(recs[0].reason).toBeTruthy();
  });
});

/* ── 4. Custom Hotkeys ─────────────────────────── */
test.describe('Custom Hotkeys (#4)', () => {
  test('Default bindings available', async ({ page }) => {
    await ready(page, '/vr/');
    const all = await page.evaluate(() => (window as any).VRComfortIntel.customHotkeys.getAll());
    expect(all.menu).toBe('n');
    expect(all.zen).toBe('z');
    expect(all.photo).toBe('p');
  });

  test('Can rebind a key', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRComfortIntel.customHotkeys.rebind('photo', 'x'));
    const key = await page.evaluate(() => (window as any).VRComfortIntel.customHotkeys.get('photo'));
    expect(key).toBe('x');
  });

  test('Editor opens and closes', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRComfortIntel.customHotkeys.openEditor());
    await page.waitForTimeout(300);
    let has = await page.evaluate(() => !!document.getElementById('vr13-hotkeys'));
    expect(has).toBe(true);
    await page.evaluate(() => (window as any).VRComfortIntel.customHotkeys.openEditor());
    await page.waitForTimeout(300);
    has = await page.evaluate(() => !!document.getElementById('vr13-hotkeys'));
    expect(has).toBe(false);
  });
});

/* ── 5. Zone Transition Effects ────────────────── */
test.describe('Transitions (#5)', () => {
  test('Default type is fade', async ({ page }) => {
    await ready(page, '/vr/');
    const type = await page.evaluate(() => (window as any).VRComfortIntel.transitions.getType());
    expect(type).toBe('fade');
  });

  test('Can set transition type', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRComfortIntel.transitions.setType('wipe'));
    const type = await page.evaluate(() => (window as any).VRComfortIntel.transitions.getType());
    expect(type).toBe('wipe');
  });
});

/* ── 6. Daily Challenge ────────────────────────── */
test.describe('Daily Challenge (#6)', () => {
  test('Challenge badge present', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr13-challenge'));
    expect(has).toBe(true);
  });

  test('Has today challenge', async ({ page }) => {
    await ready(page, '/vr/');
    const ch = await page.evaluate(() => (window as any).VRComfortIntel.dailyChallenge.getChallenge());
    expect(ch.id).toBeTruthy();
    expect(ch.desc).toBeTruthy();
  });

  test('State tracks progress', async ({ page }) => {
    await ready(page, '/vr/');
    const state = await page.evaluate(() => (window as any).VRComfortIntel.dailyChallenge.getState());
    expect(state.date).toBeTruthy();
    expect(typeof state.completed).toBe('boolean');
  });
});

/* ── 7. Comfort Settings V2 ───────────────────── */
test.describe('Comfort Settings V2 (#7)', () => {
  test('Panel opens', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRComfortIntel.comfortV2.open());
    await page.waitForTimeout(300);
    const has = await page.evaluate(() => !!document.getElementById('vr13-comfort'));
    expect(has).toBe(true);
  });

  test('Get prefs returns defaults', async ({ page }) => {
    await ready(page, '/vr/');
    const prefs = await page.evaluate(() => (window as any).VRComfortIntel.comfortV2.getPrefs());
    expect(typeof prefs.vignette).toBe('boolean');
    expect(typeof prefs.uiScale).toBe('number');
  });

  test('Can toggle vignette', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRComfortIntel.comfortV2.set('vignette', true));
    const vig = await page.evaluate(() => !!document.getElementById('vr13-vignette'));
    expect(vig).toBe(true);
    await page.evaluate(() => (window as any).VRComfortIntel.comfortV2.set('vignette', false));
    const vigOff = await page.evaluate(() => !!document.getElementById('vr13-vignette'));
    expect(vigOff).toBe(false);
  });
});

/* ── 8. Content Bookmarks ──────────────────────── */
test.describe('Bookmarks (#8)', () => {
  test('Bookmark button present', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr13-bookmarks-btn'));
    expect(has).toBe(true);
  });

  test('Can add and search bookmarks', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRComfortIntel.bookmarks.add('Test Page', '/vr/', ['test', 'demo']));
    const all = await page.evaluate(() => (window as any).VRComfortIntel.bookmarks.getAll());
    expect(all.length).toBeGreaterThanOrEqual(1);
    const results = await page.evaluate(() => (window as any).VRComfortIntel.bookmarks.search('test'));
    expect(results.length).toBeGreaterThanOrEqual(1);
  });

  test('Can remove bookmark', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRComfortIntel.bookmarks.add('Removable', '/vr/events/', []));
    const items = await page.evaluate(() => (window as any).VRComfortIntel.bookmarks.getAll());
    const id = items[0].id;
    await page.evaluate((id) => (window as any).VRComfortIntel.bookmarks.remove(id), id);
    const after = await page.evaluate(() => (window as any).VRComfortIntel.bookmarks.getAll());
    expect(after.some((b: any) => b.id === id)).toBe(false);
  });
});

/* ── 9. Session Replay ─────────────────────────── */
test.describe('Session Replay (#9)', () => {
  test('Actions are logged', async ({ page }) => {
    await ready(page, '/vr/');
    const actions = await page.evaluate(() => (window as any).VRComfortIntel.sessionReplay.getActions());
    expect(actions.length).toBeGreaterThanOrEqual(1);
    expect(actions[0].action).toBe('zone_enter');
  });

  test('Can log custom action', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRComfortIntel.sessionReplay.log('test_action', 'test detail'));
    const actions = await page.evaluate(() => (window as any).VRComfortIntel.sessionReplay.getActions());
    const last = actions[actions.length - 1];
    expect(last.action).toBe('test_action');
  });

  test('Timeline opens and closes', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRComfortIntel.sessionReplay.open());
    await page.waitForTimeout(300);
    let has = await page.evaluate(() => !!document.getElementById('vr13-replay'));
    expect(has).toBe(true);
    await page.evaluate(() => (window as any).VRComfortIntel.sessionReplay.open());
    await page.waitForTimeout(300);
    has = await page.evaluate(() => !!document.getElementById('vr13-replay'));
    expect(has).toBe(false);
  });
});

/* ── 10. Particle Density Control ──────────────── */
test.describe('Particle Density (#10)', () => {
  test('Slider present', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr13-particles'));
    expect(has).toBe(true);
  });

  test('Default density is 1.0', async ({ page }) => {
    await ready(page, '/vr/');
    const d = await page.evaluate(() => (window as any).VRComfortIntel.particleDensity.get());
    expect(d).toBe(1);
  });

  test('Can set density', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRComfortIntel.particleDensity.set(0.5));
    const d = await page.evaluate(() => (window as any).VRComfortIntel.particleDensity.get());
    expect(d).toBe(0.5);
  });
});

/* ── Cross-Zone: No JS errors ────────────────── */
test.describe('No JS errors with Set 13', () => {
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
