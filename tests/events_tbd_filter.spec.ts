/**
 * Verify TBD / Date Unavailable events are hidden by default
 * and the toggle button lets users show/hide them.
 *
 * Run: npx playwright test tests/events_tbd_filter.spec.ts --project="Desktop Chrome"
 */
import { test, expect } from '@playwright/test';

const isRemote =
  process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true';
const BASE =
  process.env.BASE_URL ||
  (isRemote ? 'https://findtorontoevents.ca' : 'http://localhost:5173');

test.describe('TBD Events Filter', () => {
  test.describe.configure({ timeout: 90000 });

  test('TBD toggle button exists and events are hidden by default', async ({ page }) => {
    await page.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 60000 });

    // Wait for events and filters to initialize
    await page.waitForTimeout(4000);

    // The TBD toggle button should exist
    const tbdBtn = page.locator('#tbd-toggle');
    await expect(tbdBtn).toBeVisible({ timeout: 10000 });
    await expect(tbdBtn).toContainText('Show TBD Events');

    // Button should NOT have the active class (TBD hidden by default)
    const hasActive = await tbdBtn.evaluate(el => el.classList.contains('active'));
    expect(hasActive).toBe(false);
  });

  test('clicking TBD toggle shows TBD events, clicking again hides them', async ({ page }) => {
    await page.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(4000);

    const tbdBtn = page.locator('#tbd-toggle');
    await expect(tbdBtn).toBeVisible({ timeout: 10000 });

    // Count visible event cards before toggle
    const visibleBefore = await page.evaluate(() => {
      const cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]');
      let visible = 0;
      cards.forEach(c => {
        const h = c.querySelector('h2, h3');
        if (!h) return;
        const hidden = c.classList.contains('event-card-hidden');
        const parentHidden = c.closest('.group')?.style.display === 'none';
        if (!hidden && !parentHidden) visible++;
      });
      return visible;
    });

    // Click TBD toggle to show TBD events
    await tbdBtn.click();
    await page.waitForTimeout(1000);

    // Button should now be active and show updated text
    const hasActiveAfterClick = await tbdBtn.evaluate(el => el.classList.contains('active'));
    expect(hasActiveAfterClick).toBe(true);
    await expect(tbdBtn).toContainText('Showing TBD Events');

    // Count visible after — should be >= before (TBD events now shown)
    const visibleAfter = await page.evaluate(() => {
      const cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]');
      let visible = 0;
      cards.forEach(c => {
        const h = c.querySelector('h2, h3');
        if (!h) return;
        const hidden = c.classList.contains('event-card-hidden');
        const parentHidden = c.closest('.group')?.style.display === 'none';
        if (!hidden && !parentHidden) visible++;
      });
      return visible;
    });
    expect(visibleAfter).toBeGreaterThanOrEqual(visibleBefore);

    // Click again to hide TBD events
    await tbdBtn.click();
    await page.waitForTimeout(1000);

    const hasActiveAfterSecond = await tbdBtn.evaluate(el => el.classList.contains('active'));
    expect(hasActiveAfterSecond).toBe(false);
    await expect(tbdBtn).toContainText('Show TBD Events');

    // Count should return to original or fewer
    const visibleFinal = await page.evaluate(() => {
      const cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]');
      let visible = 0;
      cards.forEach(c => {
        const h = c.querySelector('h2, h3');
        if (!h) return;
        const hidden = c.classList.contains('event-card-hidden');
        const parentHidden = c.closest('.group')?.style.display === 'none';
        if (!hidden && !parentHidden) visible++;
      });
      return visible;
    });
    expect(visibleFinal).toBeLessThanOrEqual(visibleAfter);
  });

  test('TBD indicator badge appears on TBD event cards', async ({ page }) => {
    await page.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(4000);

    // After initial filter pass, any TBD cards should have a .tbd-indicator badge
    const tbdIndicators = await page.locator('.tbd-indicator').count();
    console.log(`TBD indicator badges found: ${tbdIndicators}`);

    // If there are TBD events, the indicators should exist
    // (this is informational — some data sets may have 0 TBD events)
    if (tbdIndicators > 0) {
      const firstIndicator = page.locator('.tbd-indicator').first();
      await expect(firstIndicator).toHaveText('TBD');
    }
  });
});
