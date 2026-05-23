/**
 * Debug: find which nav link points to favcreators and where it comes from.
 * Run: npx playwright test tests/debug_nav_menu.spec.ts
 * Server must be running: python tools/serve_local.py
 */
import { test, expect } from '@playwright/test';

const BASE = process.env.BASE_URL || 'http://localhost:5173';

test('nav menu has no favcreators link; all point to /fc/#/guest', async ({
  page,
}) => {
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.getByTitle('Quick Navigation').click();
  await page.waitForTimeout(1000);

  const links = await page.locator('a[href]').all();
  const results: { text: string; href: string }[] = [];
  for (const link of links) {
    const href = await link.getAttribute('href');
    const text = (await link.innerText()).replace(/\s+/g, ' ').trim().slice(0, 60);
    if (href) results.push({ text, href });
  }

  const bad = results.filter(
    (r) =>
      r.href.toLowerCase().includes('favcreators') ||
      r.href === 'https://findtorontoevents.ca/fc/#/guest'
  );
  expect(
    bad,
    'No link href should contain favcreators. Bad: ' + JSON.stringify(bad)
  ).toHaveLength(0);

  const favcreatorsLabelLinks = results.filter(
    (r) => r.text.trim() === 'FAVCREATORS' || r.text.includes('Favorite Creators')
  );
  for (const r of favcreatorsLabelLinks) {
    expect(
      r.href,
      'FavCreators menu link should be /fc/#/guest, got: ' + r.href
    ).toBe('/fc/#/guest');
  }
});
