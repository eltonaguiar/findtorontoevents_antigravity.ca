import { test, expect } from '@playwright/test';

const BASE = 'http://127.0.0.1:9000';
const EVENTS_GRID = '#events-grid';
const REACT_LOAD_WAIT_MS = 15000; // wait for React app to load and render (no fallback)

test.describe('Events loading at http://127.0.0.1:9000/', () => {
  test('page loads and events grid exists', async ({ page }) => {
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    const grid = page.locator(EVENTS_GRID);
    await expect(grid).toBeVisible();
  });

  test('React app shows real event cards (links to events)', async ({ page }) => {
    await page.goto(BASE + '/', { waitUntil: 'networkidle' });
    const grid = page.locator(EVENTS_GRID);
    await expect(grid).toBeVisible();
    const eventLinks = grid.locator('a[href*="http"]');
    await expect(eventLinks.first()).toBeVisible({ timeout: REACT_LOAD_WAIT_MS });
    expect(await eventLinks.count()).toBeGreaterThan(0);
  });

  test('full UI has filter/search (GLOBAL FEED or search bar)', async ({ page }) => {
    await page.goto(BASE + '/', { waitUntil: 'networkidle' });
    await expect(
      page.getByText('GLOBAL FEED').or(page.getByPlaceholder(/search toronto events/i))
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
