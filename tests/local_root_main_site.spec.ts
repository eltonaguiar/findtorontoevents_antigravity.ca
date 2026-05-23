/**
 * Verify that the local root URL (http://localhost:5173/) serves the main events site,
 * not FavCreators. Root must not redirect to /fc/.
 *
 * Run with: npx playwright test tests/local_root_main_site.spec.ts
 * Or: npm run verify:local (includes this if matched in playwright.config)
 */
import { test, expect } from '@playwright/test';

const BASE = process.env.BASE_URL || 'http://localhost:5173';
const EVENTS_GRID = '#events-grid';

test.describe('Local root URL serves main events site', () => {
  test('root URL (/) stays on main site and does not redirect to /fc/', async ({ page }) => {
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });

    // Must not redirect to FavCreators
    const url = page.url();
    expect(url, 'Root must not redirect to /fc/').not.toMatch(/\/fc\/?(\?|#|$)/);
    expect(url, 'Root should be / or /index.html').toMatch(new RegExp(`^${BASE.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/?(index\\.html)?(\\?|#|$)`));

    // Main site: Toronto Events title and events grid
    await expect(page).toHaveTitle(/Find Toronto Events|Toronto Events/i);
    await expect(page.locator(EVENTS_GRID)).toBeVisible({ timeout: 15000 });

    // Must not be FavCreators app
    await expect(page).not.toHaveTitle(/^FavCreators$/);
    await expect(page.getByText('Access required', { exact: true })).not.toBeVisible();
  });

  test('root page has main site content (Toronto Events heading or GLOBAL FEED)', async ({ page }) => {
    await page.goto(BASE + '/', { waitUntil: 'networkidle' });

    const hasMainHeading = await page.getByText('Toronto Events', { exact: false }).first().isVisible().catch(() => false);
    const hasGlobalFeed = await page.getByText('GLOBAL FEED').first().isVisible().catch(() => false);
    const hasEventsGrid = await page.locator(EVENTS_GRID).isVisible().catch(() => false);

    expect(hasMainHeading || hasGlobalFeed || hasEventsGrid, 'Page should show main site content (Toronto Events / GLOBAL FEED / events grid)').toBeTruthy();
  });
});
