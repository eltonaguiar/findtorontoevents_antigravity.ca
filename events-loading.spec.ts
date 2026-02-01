import { test, expect } from '@playwright/test';

const BASE = process.env.BASE_URL || 'http://localhost:5173';
const EVENTS_GRID = '#events-grid';
const REACT_LOAD_WAIT_MS = 25000; // wait for React app to load and render (no fallback)

test.describe('Events loading at local root (main site)', () => {
  test('page loads and events grid exists', async ({ page }) => {
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    const grid = page.locator(EVENTS_GRID);
    await expect(grid).toBeVisible();
  });

  test('React app shows real event cards (links to events)', async ({ page }) => {
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    const grid = page.locator(EVENTS_GRID);
    await expect(grid).toBeVisible({ timeout: REACT_LOAD_WAIT_MS });
    // Wait for events.json to be fetched and React to render cards
    const eventLinks = grid.locator('a[href*="http"]');
    await expect(eventLinks.first()).toBeVisible({ timeout: REACT_LOAD_WAIT_MS });
    expect(await eventLinks.count()).toBeGreaterThan(0);
  });

  test('full UI has filter/search (GLOBAL FEED or search bar)', async ({ page }) => {
    await page.goto(BASE + '/', { waitUntil: 'networkidle' });
    await expect(
      page.getByText('GLOBAL FEED').or(page.getByPlaceholder(/search toronto events/i)).first()
    ).toBeVisible({ timeout: REACT_LOAD_WAIT_MS });
  });

  test('no critical JS errors in console', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      const text = msg.text();
      const type = msg.type();
      if (type === 'error' && (text.includes('SyntaxError') || text.includes('Unexpected token'))) {
        errors.push(text);
      }
    });
    await page.goto(BASE + '/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    expect(errors).toHaveLength(0);
  });
});
