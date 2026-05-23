/**
 * Remote site verification: findtorontoevents.ca
 * Run after coding changes to ensure the live site loads events, has no critical
 * JS errors, and key features (filters, grid, event count) work.
 *
 * Usage:
 *   npx playwright test tests/verify_remote_site.spec.ts
 *   VERIFY_REMOTE_URL=https://staging.example.com npx playwright test tests/verify_remote_site.spec.ts
 *
 * Requires: no webServer (hits live URL). Set VERIFY_REMOTE_URL or defaults to https://findtorontoevents.ca
 */

import { test, expect } from '@playwright/test';

const REMOTE_BASE =
  process.env.VERIFY_REMOTE_URL || 'https://findtorontoevents.ca';
const EVENTS_GRID = '#events-grid';
const REACT_LOAD_WAIT_MS = 35000; // allow time for network + React hydration on live

test.describe('Remote site verification: ' + REMOTE_BASE, () => {
  test('homepage loads and returns 200', async ({ page }) => {
    const res = await page.goto(REMOTE_BASE + '/', {
      waitUntil: 'domcontentloaded',
      timeout: 20000,
    });
    expect(res?.status()).toBe(200);
  });

  test('events grid is visible after React loads', async ({ page }) => {
    await page.goto(REMOTE_BASE + '/', { waitUntil: 'domcontentloaded' });
    const grid = page.locator(EVENTS_GRID);
    await expect(grid).toBeVisible({ timeout: REACT_LOAD_WAIT_MS });
  });

  test('events count > 0 (event cards or "EVENTS FOUND" text)', async ({
    page,
  }) => {
    await page.goto(REMOTE_BASE + '/', { waitUntil: 'domcontentloaded' });
    const grid = page.locator(EVENTS_GRID);
    await expect(grid).toBeVisible({ timeout: REACT_LOAD_WAIT_MS });
    await page.waitForTimeout(2000);

    // Either: event cards (links) in grid, or UI text like "945 EVENTS FOUND" / "EVENTS FOUND"
    const eventLinks = grid.locator('a[href*="http"]');
    const eventsFoundStrict = page.getByText(/\d+\s*EVENTS\s*FOUND/i);
    const eventsFoundLoose = page.getByText(/EVENTS\s*FOUND/i);
    const hasCards = (await eventLinks.count()) > 0;
    const hasCountStrict = await eventsFoundStrict.isVisible().catch(() => false);
    const hasCountLoose = await eventsFoundLoose.isVisible().catch(() => false);

    expect(
      hasCards || hasCountStrict || hasCountLoose,
      'Expected either event cards in grid or "EVENTS FOUND" text'
    ).toBeTruthy();
  });

  test('filter/search UI visible (GLOBAL FEED or search bar)', async ({
    page,
  }) => {
    await page.goto(REMOTE_BASE + '/', { waitUntil: 'networkidle' });
    await expect(
      page
        .getByText('GLOBAL FEED')
        .or(page.getByPlaceholder(/search toronto events/i))
        .first()
    ).toBeVisible({ timeout: REACT_LOAD_WAIT_MS });
  });

  test('no critical JS errors in console', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      const text = msg.text();
      const type = msg.type();
      if (
        type === 'error' &&
        (text.includes('SyntaxError') ||
          text.includes('Unexpected token') ||
          text.includes('ChunkLoadError') ||
          text.includes('Loading chunk') ||
          text.includes('denied by modsecurity'))
      ) {
        errors.push(text);
      }
    });
    await page.goto(REMOTE_BASE + '/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    expect(
      errors,
      'Critical JS errors: ' + (errors.length ? errors.join('; ') : 'none')
    ).toHaveLength(0);
  });

  test('main chunk returns JS (not HTML or blocked)', async ({ request }) => {
    // Fetch index to get chunk URL, or use known chunk path
    const indexRes = await request.get(REMOTE_BASE + '/');
    expect(indexRes.ok()).toBeTruthy();
    const html = await indexRes.text();
    const chunkMatch = html.match(
      /\/next\/_next\/static\/chunks\/(a2ac3a6616d60872\.js)(?:\?[^"'\s]*)?/
    );
    const chunkPath = chunkMatch
      ? '/next/_next/static/chunks/' + chunkMatch[1]
      : '/next/_next/static/chunks/a2ac3a6616d60872.js';
    const chunkUrl = REMOTE_BASE.replace(/\/$/, '') + chunkPath;
    const chunkRes = await request.get(chunkUrl);
    expect(chunkRes.ok(), `Chunk ${chunkUrl} should return 200`).toBeTruthy();
    const body = await chunkRes.text();
    expect(
      body.includes('TURBOPACK') || body.includes('(function'),
      'Chunk response should be JavaScript'
    ).toBeTruthy();
    expect(
      body.startsWith('<!') || body.toLowerCase().includes('denied by modsecurity'),
      'Chunk should not be HTML or ModSecurity block'
    ).toBeFalsy();
  });

  test('Quick Nav opens and FavCreators link is /fc/#/guest (menu fix)', async ({
    page,
  }) => {
    await page.goto(REMOTE_BASE + '/', { waitUntil: 'networkidle' });
    await page.getByTitle('Quick Navigation').click();
    await page.waitForTimeout(800);
    const favLink = page.getByRole('link', { name: 'FAVCREATORS' });
    await expect(favLink).toBeVisible({ timeout: 5000 });
    const href = await favLink.getAttribute('href');
    // FavCreators is at /fc/#/guest (path "favcreators" returns 500 on host)
    expect(href, 'FavCreators menu link must be /fc/#/guest').toBe('/fc/#/guest');
    // Ensure no link in the page points to broken /favcreators/
    const allLinks = await page.locator('a[href*="favcreators"]').count();
    expect(
      allLinks,
      'No link href should contain "favcreators" (use /fc/#/guest)'
    ).toBe(0);
  });
});
