import { test, expect, Page } from '@playwright/test';

/**
 * VR Polish, Productivity & Accessibility — Set 15 Tests
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
test.describe('Set 15 Core Loading', () => {
  test('Hub: VRPolish global available', async ({ page }) => {
    const errs = await jsErrors(page);
    await ready(page, '/vr/');
    expect(await page.evaluate(() => typeof (window as any).VRPolish === 'object')).toBe(true);
    expect(await page.evaluate(() => (window as any).VRPolish.version)).toBe(15);
    expect(errs.length).toBe(0);
  });

  for (const z of [
    { name: 'Events', url: '/vr/events/', zone: 'events' },
    { name: 'Movies', url: '/vr/movies.html', zone: 'movies' },
    { name: 'Stocks', url: '/vr/stocks-zone.html', zone: 'stocks' },
  ]) {
    test(`${z.name}: loaded`, async ({ page }) => {
      const errs = await jsErrors(page);
      await ready(page, z.url);
      expect(await page.evaluate(() => (window as any).VRPolish?.zone)).toBe(z.zone);
      expect(errs.length).toBe(0);
    });
  }
});

/* ── 1. Keyboard Map ───────────────────────────── */
test.describe('Keyboard Map (#1)', () => {
  test('Opens and closes', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPolish.keyboardMap.toggle());
    await page.waitForTimeout(300);
    let has = await page.evaluate(() => !!document.getElementById('vr15-keymap'));
    expect(has).toBe(true);
    await page.evaluate(() => (window as any).VRPolish.keyboardMap.toggle());
    await page.waitForTimeout(300);
    has = await page.evaluate(() => !!document.getElementById('vr15-keymap'));
    expect(has).toBe(false);
  });

  test('Has 13+ shortcuts', async ({ page }) => {
    await ready(page, '/vr/');
    const shortcuts = await page.evaluate(() => (window as any).VRPolish.keyboardMap.getShortcuts());
    expect(shortcuts.length).toBeGreaterThanOrEqual(13);
  });
});

/* ── 2. Color Blind Modes ──────────────────────── */
test.describe('Color Blind (#2)', () => {
  test('Default is none', async ({ page }) => {
    await ready(page, '/vr/');
    const mode = await page.evaluate(() => (window as any).VRPolish.colorBlind.getMode());
    expect(mode).toBe('none');
  });

  test('Can apply deuteranopia', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPolish.colorBlind.apply('deuteranopia'));
    const mode = await page.evaluate(() => (window as any).VRPolish.colorBlind.getMode());
    expect(mode).toBe('deuteranopia');
    const attr = await page.evaluate(() => document.body.getAttribute('data-cb-mode'));
    expect(attr).toBe('deuteranopia');
  });

  test('Has 4 modes', async ({ page }) => {
    await ready(page, '/vr/');
    const modes = await page.evaluate(() => (window as any).VRPolish.colorBlind.modes);
    expect(modes.length).toBe(4);
  });

  test('Cycle advances mode', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPolish.colorBlind.apply('none'));
    await page.evaluate(() => (window as any).VRPolish.colorBlind.cycle());
    const mode = await page.evaluate(() => (window as any).VRPolish.colorBlind.getMode());
    expect(mode).not.toBe('none');
  });
});

/* ── 3. Focus Timer (Pomodoro) ─────────────────── */
test.describe('Pomodoro (#3)', () => {
  test('Timer UI present', async ({ page }) => {
    await ready(page, '/vr/');
    const has = await page.evaluate(() => !!document.getElementById('vr15-pomo'));
    expect(has).toBe(true);
  });

  test('Start work sets phase', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPolish.focusTimer.startWork());
    const state = await page.evaluate(() => (window as any).VRPolish.focusTimer.getState());
    expect(state.phase).toBe('work');
    expect(state.running).toBe(true);
    expect(state.remaining).toBeGreaterThan(0);
    await page.evaluate(() => (window as any).VRPolish.focusTimer.stop());
  });

  test('Start break sets phase', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPolish.focusTimer.startBreak());
    const state = await page.evaluate(() => (window as any).VRPolish.focusTimer.getState());
    expect(state.phase).toBe('break');
    await page.evaluate(() => (window as any).VRPolish.focusTimer.stop());
  });
});

/* ── 4. Content Tagging ────────────────────────── */
test.describe('Tagging (#4)', () => {
  test('Add and get tags', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => {
      (window as any).VRPolish.tagging.add('item1', 'fun');
      (window as any).VRPolish.tagging.add('item1', 'vr');
    });
    const tags = await page.evaluate(() => (window as any).VRPolish.tagging.get('item1'));
    expect(tags).toContain('fun');
    expect(tags).toContain('vr');
  });

  test('Search by tag', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => {
      (window as any).VRPolish.tagging.add('itemA', 'test');
      (window as any).VRPolish.tagging.add('itemB', 'test');
    });
    const results = await page.evaluate(() => (window as any).VRPolish.tagging.search('test'));
    expect(results.length).toBeGreaterThanOrEqual(2);
  });

  test('Get all returns counts', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPolish.tagging.add('x', 'demo'));
    const all = await page.evaluate(() => (window as any).VRPolish.tagging.getAll());
    expect(typeof all).toBe('object');
    expect(all.demo).toBeGreaterThanOrEqual(1);
  });
});

/* ── 5. Multi-Tab Sync ─────────────────────────── */
test.describe('Tab Sync (#5)', () => {
  test('API available', async ({ page }) => {
    await ready(page, '/vr/');
    expect(await page.evaluate(() => typeof (window as any).VRPolish.tabSync.broadcast)).toBe('function');
  });

  test('isSupported returns boolean', async ({ page }) => {
    await ready(page, '/vr/');
    const sup = await page.evaluate(() => (window as any).VRPolish.tabSync.isSupported());
    expect(typeof sup).toBe('boolean');
  });
});

/* ── 6. QR Code Sharing ───────────────────────── */
test.describe('QR Sharing (#6)', () => {
  test('Generate returns URL', async ({ page }) => {
    await ready(page, '/vr/');
    const url = await page.evaluate(() => (window as any).VRPolish.qrSharing.generate('https://example.com'));
    expect(url).toContain('chart.googleapis.com');
  });

  test('Show opens dialog', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPolish.qrSharing.show());
    await page.waitForTimeout(300);
    const has = await page.evaluate(() => !!document.getElementById('vr15-qr'));
    expect(has).toBe(true);
  });
});

/* ── 7. Command Palette ────────────────────────── */
test.describe('Command Palette (#7)', () => {
  test('Opens with input', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPolish.commandPalette.open());
    await page.waitForTimeout(300);
    const has = await page.evaluate(() => !!document.getElementById('vr15-palette'));
    expect(has).toBe(true);
  });

  test('Has 20 commands', async ({ page }) => {
    await ready(page, '/vr/');
    const cmds = await page.evaluate(() => (window as any).VRPolish.commandPalette.getCommands());
    expect(cmds.length).toBe(20);
  });

  test('Closes on toggle', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPolish.commandPalette.open());
    await page.waitForTimeout(300);
    await page.evaluate(() => (window as any).VRPolish.commandPalette.open());
    await page.waitForTimeout(300);
    const has = await page.evaluate(() => !!document.getElementById('vr15-palette'));
    expect(has).toBe(false);
  });
});

/* ── 8. History Graph ──────────────────────────── */
test.describe('History Graph (#8)', () => {
  test('getData returns zone data', async ({ page }) => {
    await ready(page, '/vr/');
    const data = await page.evaluate(() => (window as any).VRPolish.historyGraph.getData());
    expect(typeof data).toBe('object');
    expect('hub' in data).toBe(true);
  });

  test('Opens and closes', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPolish.historyGraph.open());
    await page.waitForTimeout(300);
    let has = await page.evaluate(() => !!document.getElementById('vr15-graph'));
    expect(has).toBe(true);
    await page.evaluate(() => (window as any).VRPolish.historyGraph.open());
    await page.waitForTimeout(300);
    has = await page.evaluate(() => !!document.getElementById('vr15-graph'));
    expect(has).toBe(false);
  });
});

/* ── 9. Auto-Save State ───────────────────────── */
test.describe('Auto-Save (#9)', () => {
  test('Save creates snapshot', async ({ page }) => {
    await ready(page, '/vr/');
    await page.evaluate(() => (window as any).VRPolish.autoSave.save());
    const snaps = await page.evaluate(() => (window as any).VRPolish.autoSave.getSnapshots());
    expect(snaps.length).toBeGreaterThanOrEqual(1);
    expect(snaps[snaps.length - 1].zone).toBeTruthy();
  });
});

/* ── 10. Haptic Feedback ──────────────────────── */
test.describe('Haptics (#10)', () => {
  test('API available', async ({ page }) => {
    await ready(page, '/vr/');
    expect(await page.evaluate(() => typeof (window as any).VRPolish.haptics.vibrate)).toBe('function');
  });

  test('Patterns listed', async ({ page }) => {
    await ready(page, '/vr/');
    const patterns = await page.evaluate(() => (window as any).VRPolish.haptics.patterns);
    expect(patterns.length).toBeGreaterThanOrEqual(5);
    expect(patterns).toContain('click');
    expect(patterns).toContain('success');
  });

  test('Enabled by default', async ({ page }) => {
    await ready(page, '/vr/');
    expect(await page.evaluate(() => (window as any).VRPolish.haptics.isEnabled())).toBe(true);
  });
});

/* ── Cross-Zone: No JS errors ────────────────── */
test.describe('No JS errors with Set 15', () => {
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
