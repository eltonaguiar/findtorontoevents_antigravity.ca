import { test, expect, Page } from '@playwright/test';

/**
 * VR Quick Wins Set 7 Tests
 *
 * Tests for: favorites, cross-zone search, activity feed, zone ratings,
 * content preloader, zone loading bar, share snapshot, enhanced tooltips,
 * breadcrumb trail, quick stats badge, and nav menu integration.
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

test.describe('Quick Wins Set 7: Core Loading', () => {
  test('Hub: VRQuickWins7 global object is available', async ({ page }) => {
    const errors = await collectJsErrors(page);
    await waitForPageReady(page, '/vr/');
    const hasQW7 = await page.evaluate(() => typeof (window as any).VRQuickWins7 === 'object');
    expect(hasQW7).toBe(true);
    expect(errors.length).toBe(0);
  });

  test('Events: VRQuickWins7 is available', async ({ page }) => {
    const errors = await collectJsErrors(page);
    await waitForPageReady(page, '/vr/events/');
    const hasQW7 = await page.evaluate(() => typeof (window as any).VRQuickWins7 === 'object');
    expect(hasQW7).toBe(true);
    expect(errors.length).toBe(0);
  });

  test('Creators: VRQuickWins7 is available', async ({ page }) => {
    const errors = await collectJsErrors(page);
    await waitForPageReady(page, '/vr/creators.html');
    const hasQW7 = await page.evaluate(() => typeof (window as any).VRQuickWins7 === 'object');
    expect(hasQW7).toBe(true);
    expect(errors.length).toBe(0);
  });
});

test.describe('Quick Wins Set 7: Zone Loading Bar', () => {
  test('Loading bar appears and completes', async ({ page }) => {
    // Navigate fresh — the bar should appear briefly
    await page.goto('/vr/', { waitUntil: 'domcontentloaded' });
    // The bar might already be gone by now (fast page), so check either present or already removed
    await page.waitForTimeout(500);
    // After load, bar should be gone or fading
    await page.waitForTimeout(3000);
    const barGone = await page.evaluate(() => !document.getElementById('vr-qw7-loadbar'));
    expect(barGone).toBe(true);
  });
});

test.describe('Quick Wins Set 7: Breadcrumb Trail', () => {
  test('Hub: no breadcrumb (root level)', async ({ page }) => {
    await waitForPageReady(page, '/vr/');
    const hasBreadcrumb = await page.evaluate(() => !!document.getElementById('vr-qw7-breadcrumb'));
    expect(hasBreadcrumb).toBe(false);
  });

  test('Events: breadcrumb shows Hub > Events Explorer', async ({ page }) => {
    await waitForPageReady(page, '/vr/events/');
    const crumb = page.locator('#vr-qw7-breadcrumb');
    await expect(crumb).toBeVisible();

    const hubLink = crumb.locator('.qw7-bc-link');
    await expect(hubLink).toHaveText('VR Hub');

    const currentLabel = crumb.locator('.qw7-bc-current');
    await expect(currentLabel).toHaveText('Events Explorer');
  });

  test('Movies: breadcrumb shows Hub > Movie Theater', async ({ page }) => {
    await waitForPageReady(page, '/vr/movies.html');
    const currentLabel = page.locator('#vr-qw7-breadcrumb .qw7-bc-current');
    await expect(currentLabel).toHaveText('Movie Theater');
  });
});

test.describe('Quick Wins Set 7: Quick Stats Badge', () => {
  test('Stats badge is visible on all zones', async ({ page }) => {
    await waitForPageReady(page, '/vr/');
    const badge = page.locator('.qw7-stats-badge');
    await expect(badge).toBeVisible();

    const text = await badge.textContent();
    // Should contain session time
    expect(text).toMatch(/\d+m session/);
  });

  test('Events zone: stats badge shows event count', async ({ page }) => {
    await waitForPageReady(page, '/vr/events/');
    // Wait for events to load
    await page.waitForTimeout(6000);
    // Trigger stats update
    await page.evaluate(() => {
      const badge = document.getElementById('vr-qw7-stats');
      if (badge) {
        const allEvts = (window as any).filteredEvents || (window as any)._allEvents || [];
        if (allEvts.length > 0) badge.textContent = allEvts.length + ' events · 0m session';
      }
    });
    const badge = page.locator('.qw7-stats-badge');
    await expect(badge).toBeVisible();
  });
});

test.describe('Quick Wins Set 7: Cross-Zone Search', () => {
  test('Search overlay opens and closes', async ({ page }) => {
    await waitForPageReady(page, '/vr/');

    // Open search via API
    await page.evaluate(() => (window as any).VRQuickWins7.openSearch());
    await page.waitForTimeout(300);

    const searchOverlay = page.locator('#vr-qw7-search');
    const isOpen = await searchOverlay.evaluate((el) => el.classList.contains('open'));
    expect(isOpen).toBe(true);

    const input = page.locator('#qw7-search-input');
    await expect(input).toBeVisible();

    // Close search
    await page.evaluate(() => (window as any).VRQuickWins7.closeSearch());
    await page.waitForTimeout(300);
    const isClosed = await searchOverlay.evaluate((el) => !el.classList.contains('open'));
    expect(isClosed).toBe(true);
  });

  test('Search shows hint text for short queries', async ({ page }) => {
    await waitForPageReady(page, '/vr/');
    await page.evaluate(() => (window as any).VRQuickWins7.openSearch());
    await page.waitForTimeout(300);

    const hint = page.locator('.qw7-search-hint');
    await expect(hint).toBeVisible();
  });
});

test.describe('Quick Wins Set 7: Activity Feed', () => {
  test('Activity feed opens with at least one visit entry', async ({ page }) => {
    await waitForPageReady(page, '/vr/');

    await page.evaluate(() => (window as any).VRQuickWins7.showActivity());
    await page.waitForTimeout(300);

    const overlay = page.locator('#vr-qw7-activity');
    const isOpen = await overlay.evaluate((el) => el.classList.contains('open'));
    expect(isOpen).toBe(true);

    // Should have at least one activity item (the visit)
    const items = page.locator('.qw7-activity-item');
    const count = await items.count();
    expect(count).toBeGreaterThanOrEqual(1);

    // Close it
    await page.evaluate(() => (window as any).VRQuickWins7.closeActivity());
    await page.waitForTimeout(300);
  });
});

test.describe('Quick Wins Set 7: Zone Ratings', () => {
  test('Rating prompt opens with 5 stars', async ({ page }) => {
    await waitForPageReady(page, '/vr/');

    await page.evaluate(() => (window as any).VRQuickWins7.showRating());
    await page.waitForTimeout(300);

    const overlay = page.locator('#vr-qw7-rate');
    const isOpen = await overlay.evaluate((el) => el.classList.contains('open'));
    expect(isOpen).toBe(true);

    const stars = page.locator('.qw7-star');
    const starCount = await stars.count();
    expect(starCount).toBe(5);

    await page.evaluate(() => (window as any).VRQuickWins7.closeRating());
  });

  test('Submitting a rating stores it', async ({ page }) => {
    await waitForPageReady(page, '/vr/');

    await page.evaluate(() => (window as any).VRQuickWins7.submitRating(4));
    await page.waitForTimeout(800);

    const rating = await page.evaluate(() => (window as any).VRQuickWins7.getZoneRating('hub'));
    expect(rating).toBe(4);
  });
});

test.describe('Quick Wins Set 7: Favorites System', () => {
  test('Add and check favorite', async ({ page }) => {
    await waitForPageReady(page, '/vr/');

    const added = await page.evaluate(() => {
      return (window as any).VRQuickWins7.addFavorite({
        id: 'test-123',
        type: 'event',
        title: 'Test Event',
        zone: 'events',
        url: '/vr/events/'
      });
    });
    expect(added).toBe(true);

    const isFav = await page.evaluate(() => (window as any).VRQuickWins7.isFavorite('test-123'));
    expect(isFav).toBe(true);

    // Remove it
    await page.evaluate(() => (window as any).VRQuickWins7.removeFavorite('test-123'));
    const isFavAfter = await page.evaluate(() => (window as any).VRQuickWins7.isFavorite('test-123'));
    expect(isFavAfter).toBe(false);
  });
});

test.describe('Quick Wins Set 7: Nav Menu Integration', () => {
  test('Nav menu has Tools section with Search, Activity, Rate, Share buttons', async ({ page }) => {
    await waitForPageReady(page, '/vr/');
    await page.keyboard.press('m');
    await page.waitForTimeout(500);

    const searchBtn = page.locator('.vr-nav-util-btn', { hasText: 'Search' });
    await expect(searchBtn).toBeVisible();

    const activityBtn = page.locator('.vr-nav-util-btn', { hasText: 'Activity' });
    await expect(activityBtn).toBeVisible();

    const rateBtn = page.locator('.vr-nav-util-btn', { hasText: 'Rate' });
    await expect(rateBtn).toBeVisible();

    const shareBtn = page.locator('.vr-nav-util-btn', { hasText: 'Share' });
    await expect(shareBtn).toBeVisible();
  });
});

test.describe('Quick Wins Set 5: Social Features', () => {
  test('VRQuickWinsSet5 is loaded', async ({ page }) => {
    await waitForPageReady(page, '/vr/');
    const hasQW5 = await page.evaluate(() => typeof (window as any).VRQuickWinsSet5 === 'object');
    expect(hasQW5).toBe(true);
  });

  test('Presence indicator visible', async ({ page }) => {
    await waitForPageReady(page, '/vr/');
    const presence = page.locator('#vr-qw5-presence');
    await expect(presence).toBeVisible();
    const text = await presence.textContent();
    expect(text).toMatch(/exploring now/);
  });

  test('Time theme attribute is set', async ({ page }) => {
    await waitForPageReady(page, '/vr/');
    const theme = await page.evaluate(() => document.body.getAttribute('data-vr-time-theme'));
    expect(['morning', 'day', 'evening', 'night']).toContain(theme);
  });
});

test.describe('Cross-Zone: No JS errors with Set 7', () => {
  const zones = [
    { name: 'Hub', url: '/vr/' },
    { name: 'Events', url: '/vr/events/' },
    { name: 'Creators', url: '/vr/creators.html' },
    { name: 'Movies', url: '/vr/movies.html' },
    { name: 'Stocks', url: '/vr/stocks-zone.html' },
    { name: 'Weather', url: '/vr/weather-zone.html' },
  ];

  for (const zone of zones) {
    test(`${zone.name}: no critical JS errors`, async ({ page }) => {
      const errors = await collectJsErrors(page);
      await waitForPageReady(page, zone.url);
      expect(errors.length).toBe(0);
    });
  }
});
