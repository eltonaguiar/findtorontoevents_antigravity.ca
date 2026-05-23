import { test, expect, Page } from '@playwright/test';

/**
 * VR Area Guide & Events Audio Tests
 *
 * Tests the area guide overlay, TTS controls, event audio announcements,
 * and event preview features across VR zones.
 */

const KNOWN_BENIGN_ERRORS = [
  'Unexpected identifier',
  'registerMaterial',
  'registerShader',
  'favicon.ico',
  'net::ERR',
  'already registered',
];

function isBenignError(msg: string): boolean {
  return KNOWN_BENIGN_ERRORS.some((k) => msg.includes(k));
}

async function collectJsErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];
  page.on('pageerror', (e) => {
    if (!isBenignError(e.message)) errors.push(e.message);
  });
  return errors;
}

async function waitForPageReady(page: Page, url: string, timeout = 15000) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout });
  await page.waitForTimeout(2000);
}

test.describe('Area Guide System', () => {
  test('Hub: area-guide.js loads and VRAreaGuide is available', async ({ page }) => {
    const errors = await collectJsErrors(page);
    await waitForPageReady(page, '/vr/');
    const hasGuide = await page.evaluate(() => typeof (window as any).VRAreaGuide === 'object');
    expect(hasGuide).toBe(true);
    expect(errors.length).toBe(0);
  });

  test('Hub: G key opens area guide overlay', async ({ page }) => {
    await waitForPageReady(page, '/vr/');
    const guideBefore = await page.locator('#vr-area-guide').evaluate((el) => el.classList.contains('open'));
    expect(guideBefore).toBe(false);

    await page.keyboard.press('g');
    await page.waitForTimeout(300);
    const guideAfter = await page.locator('#vr-area-guide').evaluate((el) => el.classList.contains('open'));
    expect(guideAfter).toBe(true);

    const title = await page.locator('.guide-title').textContent();
    expect(title).toContain('VR Hub');
  });

  test('Hub: guide overlay has zone-specific actions', async ({ page }) => {
    await waitForPageReady(page, '/vr/');
    await page.keyboard.press('g');
    await page.waitForTimeout(300);

    const actionCount = await page.locator('.guide-actions li').count();
    expect(actionCount).toBeGreaterThanOrEqual(3);

    const readAloudBtn = page.locator('.guide-tts-btn', { hasText: 'Read Aloud' });
    await expect(readAloudBtn).toBeVisible();
  });

  test('Hub: G key toggles guide closed', async ({ page }) => {
    await waitForPageReady(page, '/vr/');
    await page.keyboard.press('g');
    await page.waitForTimeout(300);
    const open = await page.locator('#vr-area-guide').evaluate((el) => el.classList.contains('open'));
    expect(open).toBe(true);

    await page.keyboard.press('g');
    await page.waitForTimeout(300);
    const closed = await page.locator('#vr-area-guide').evaluate((el) => el.classList.contains('open'));
    expect(closed).toBe(false);
  });

  test('Hub: close button closes guide overlay', async ({ page }) => {
    await waitForPageReady(page, '/vr/');
    await page.keyboard.press('g');
    await page.waitForTimeout(300);
    await page.locator('.guide-close').click();
    await page.waitForTimeout(300);
    const closed = await page.locator('#vr-area-guide').evaluate((el) => el.classList.contains('open'));
    expect(closed).toBe(false);
  });
});

test.describe('Nav Menu Guide Integration', () => {
  test('Nav menu has Guide buttons', async ({ page }) => {
    await waitForPageReady(page, '/vr/');
    await page.keyboard.press('m');
    await page.waitForTimeout(500);

    const guideBtn = page.locator('.vr-nav-guide-btn', { hasText: 'About This Zone' });
    await expect(guideBtn).toBeVisible();

    const speakBtn = page.locator('.vr-nav-guide-btn.vr-nav-guide-speak', { hasText: 'Read Aloud' });
    await expect(speakBtn).toBeVisible();
  });

  test('Nav menu footer mentions G key', async ({ page }) => {
    await waitForPageReady(page, '/vr/');
    await page.keyboard.press('m');
    await page.waitForTimeout(500);
    const hint = await page.locator('.vr-nav-hint').textContent();
    expect(hint).toContain('G');
    expect(hint).toContain('Area Guide');
  });
});

test.describe('Events Zone: Area Guide + Audio', () => {
  test('Events: area guide shows event-specific content', async ({ page }) => {
    await waitForPageReady(page, '/vr/events/');
    await page.keyboard.press('g');
    await page.waitForTimeout(300);

    const title = await page.locator('.guide-title').textContent();
    expect(title).toContain('Events Explorer');

    const actions = await page.locator('.guide-actions li').allTextContents();
    const hasSearchAction = actions.some((a) => a.toLowerCase().includes('search'));
    expect(hasSearchAction).toBe(true);
  });

  test('Events: guide has Event Announcements section', async ({ page }) => {
    await waitForPageReady(page, '/vr/events/');
    await page.keyboard.press('g');
    await page.waitForTimeout(300);

    const audioSection = page.locator('.guide-event-audio');
    await expect(audioSection).toBeVisible();

    const todayBtn = page.locator('.guide-event-btn', { hasText: "Today's Events" });
    await expect(todayBtn).toBeVisible();

    const tomorrowBtn = page.locator('.guide-event-btn', { hasText: "Tomorrow's Events" });
    await expect(tomorrowBtn).toBeVisible();

    const weekendBtn = page.locator('.guide-event-btn', { hasText: 'This Weekend' });
    await expect(weekendBtn).toBeVisible();
  });

  test('Events: audio bar is visible with today/tomorrow/weekend buttons', async ({ page }) => {
    await waitForPageReady(page, '/vr/events/');

    const audioBar = page.locator('#events-audio-bar');
    await expect(audioBar).toBeVisible();

    const buttons = await audioBar.locator('.evt-audio-btn').allTextContents();
    expect(buttons).toContain('Today');
    expect(buttons).toContain('Tomorrow');
    expect(buttons).toContain('Weekend');
  });

  test('Events: pause/stop buttons hidden by default', async ({ page }) => {
    await waitForPageReady(page, '/vr/events/');
    const pauseBtn = page.locator('#evt-pause-btn');
    await expect(pauseBtn).toBeHidden();
    const stopBtn = page.locator('#evt-stop-btn');
    await expect(stopBtn).toBeHidden();
  });
});

test.describe('Events Zone: Event Preview', () => {
  test('Events: preview overlay exists and is hidden by default', async ({ page }) => {
    await waitForPageReady(page, '/vr/events/');
    const preview = page.locator('#event-preview');
    const isHidden = await preview.evaluate((el) => !el.classList.contains('open'));
    expect(isHidden).toBe(true);
  });

  test('Events: detail overlay has Preview button', async ({ page }) => {
    await waitForPageReady(page, '/vr/events/');
    await page.waitForTimeout(5000);

    const cards = page.locator('.event-card, [data-gidx]');
    const cardCount = await cards.count();
    if (cardCount > 0) {
      await cards.first().click();
      await page.waitForTimeout(300);
      const previewBtn = page.locator('#event-detail .btn', { hasText: 'Preview' });
      await expect(previewBtn).toBeVisible();
    }
  });
});

test.describe('Creators Zone: Area Guide', () => {
  test('Creators: area guide shows live context', async ({ page }) => {
    await waitForPageReady(page, '/vr/creators.html');
    await page.keyboard.press('g');
    await page.waitForTimeout(300);

    const title = await page.locator('.guide-title').textContent();
    expect(title).toContain('FavCreators');

    const actions = await page.locator('.guide-actions li').allTextContents();
    const hasLoginAction = actions.some((a) => a.toLowerCase().includes('login'));
    expect(hasLoginAction).toBe(true);
  });
});

test.describe('Other Zones: Area Guide', () => {
  test('Movies: area guide loads correctly', async ({ page }) => {
    await waitForPageReady(page, '/vr/movies.html');
    const hasGuide = await page.evaluate(() => typeof (window as any).VRAreaGuide === 'object');
    expect(hasGuide).toBe(true);

    await page.keyboard.press('g');
    await page.waitForTimeout(300);
    const title = await page.locator('.guide-title').textContent();
    expect(title).toContain('Movie Theater');
  });

  test('Stocks: area guide loads correctly', async ({ page }) => {
    await waitForPageReady(page, '/vr/stocks-zone.html');
    await page.keyboard.press('g');
    await page.waitForTimeout(300);
    const title = await page.locator('.guide-title').textContent();
    expect(title).toContain('Trading Floor');
  });

  test('Weather: area guide loads correctly', async ({ page }) => {
    await waitForPageReady(page, '/vr/weather-zone.html');
    await page.keyboard.press('g');
    await page.waitForTimeout(300);
    const title = await page.locator('.guide-title').textContent();
    expect(title).toContain('Weather Observatory');
  });

  test('Tutorial: area guide loads correctly', async ({ page }) => {
    await waitForPageReady(page, '/vr/tutorial/');
    await page.keyboard.press('g');
    await page.waitForTimeout(300);
    const title = await page.locator('.guide-title').textContent();
    expect(title).toContain('Tutorial');
  });
});

test.describe('Cross-Zone: No JS errors with area guide', () => {
  const zones = [
    { name: 'Hub', url: '/vr/' },
    { name: 'Events', url: '/vr/events/' },
    { name: 'Creators', url: '/vr/creators.html' },
    { name: 'Movies', url: '/vr/movies.html' },
    { name: 'Stocks', url: '/vr/stocks-zone.html' },
  ];

  for (const zone of zones) {
    test(`${zone.name}: no critical JS errors`, async ({ page }) => {
      const errors = await collectJsErrors(page);
      await waitForPageReady(page, zone.url);
      expect(errors.length).toBe(0);
    });
  }
});
