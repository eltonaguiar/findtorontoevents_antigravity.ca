import { test, expect } from '@playwright/test';

/**
 * Verifies the 🎮 Dexerto News section in the weather page right panel
 * renders real article links from the /weather/api/dexerto_news.php endpoint
 * instead of the "Dexerto news unavailable" fallback state.
 */
test('weather right panel Dexerto section renders real articles', async ({ page }) => {
  await page.goto('/weather/', { waitUntil: 'domcontentloaded', timeout: 45000 });

  // loadSideDexerto() runs ~1.5s after load and fetches the endpoint.
  // Wait until at least one real article link appears in the #side-dexerto list.
  await page.waitForSelector('#side-dexerto li a', { timeout: 35000 });

  const links = page.locator('#side-dexerto li a');
  const count = await links.count();
  expect(count).toBeGreaterThan(0);

  const firstTitle = (await links.first().textContent()) ?? '';
  expect(firstTitle.trim().length).toBeGreaterThan(10);

  // The fallback "unavailable" / "No Dexerto news" states must NOT be present.
  const emptyCount = await page.locator('#side-dexerto .side-empty').count();
  expect(emptyCount).toBe(0);

  // Links should point to dexerto.com (real Dexerto articles).
  const firstHref = await links.first().getAttribute('href');
  expect(firstHref ?? '').toContain('dexerto.com');
});
