import { test, expect } from '@playwright/test';

/**
 * Validates the bottom-right gear (settings) icon survives React hydration.
 * Bug: React error #418 causes a full client re-render that destroys
 * non-React DOM nodes inside the fixed-ui-layer. The gear FAB must be
 * re-injected by the MutationObserver after hydration completes.
 */

const URLS = [
  'https://findtorontoevents.ca/',
  'https://torontoevent.net/',
];

for (const url of URLS) {
  const host = new URL(url).hostname;

  test(`[${host}] gear icon is visible in bottom-right after hydration`, async ({ page }) => {
    // Navigate and wait for React hydration to complete
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });

    // Wait extra time for React hydration + MutationObserver re-injection
    await page.waitForTimeout(6000);

    // The gear FAB should exist with id="settings-gear-fab" (re-injected version)
    // OR as a button with title="Configuration Settings (Always Accessible)"
    const gearFab = page.locator('#settings-gear-fab, [title="Configuration Settings (Always Accessible)"]').first();

    // It must exist in the DOM
    await expect(gearFab).toBeAttached({ timeout: 10000 });

    // It must be visible (not hidden by React or CSS)
    await expect(gearFab).toBeVisible({ timeout: 5000 });

    // Verify it's in the bottom-right quadrant of the viewport
    const box = await gearFab.boundingBox();
    expect(box).not.toBeNull();
    if (box) {
      const viewport = page.viewportSize()!;
      // Bottom-right means: x > 50% of viewport width, y > 50% of viewport height
      expect(box.x + box.width / 2).toBeGreaterThan(viewport.width * 0.5);
      expect(box.y + box.height / 2).toBeGreaterThan(viewport.height * 0.5);
    }

    // Verify it contains an SVG (the gear icon, not just an empty div)
    const svg = gearFab.locator('svg').first();
    await expect(svg).toBeAttached();
  });

  test(`[${host}] gear icon persists after page interactions`, async ({ page }) => {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(6000);

    // Scroll down to trigger any lazy-loading or re-renders
    await page.evaluate(() => window.scrollBy(0, 500));
    await page.waitForTimeout(1000);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(1000);

    // Gear should still be visible
    const gearFab = page.locator('#settings-gear-fab, [title="Configuration Settings (Always Accessible)"]').first();
    await expect(gearFab).toBeVisible({ timeout: 5000 });
  });
}
