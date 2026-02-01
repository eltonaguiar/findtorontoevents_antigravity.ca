/**
 * Verify 2XKO Frame Data appears after FAVCREATORS in Quick Nav (local).
 * Run: npx playwright test tests/nav_2xko_after_favcreators.spec.ts
 */
import { test, expect } from '@playwright/test';

const BASE = process.env.BASE_URL || 'http://localhost:5173';

test('2XKO Frame Data is below FAVCREATORS in Quick Nav', async ({ page }) => {
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.getByTitle('Quick Navigation').click();
  await page.waitForTimeout(800);

  const nav = page.locator('nav');
  await expect(nav).toBeVisible();

  const links = nav.locator('a[href]');
  const texts: string[] = [];
  const count = await links.count();
  for (let i = 0; i < count; i++) {
    const t = await links.nth(i).textContent();
    if (t) texts.push(t.trim());
  }

  const idxFav = texts.findIndex((t) => t.includes('FAVCREATORS'));
  const idx2xko = texts.findIndex((t) => t.includes('2XKO Frame Data'));

  expect(idxFav, 'FAVCREATORS link should exist in nav').toBeGreaterThanOrEqual(0);
  expect(idx2xko, '2XKO Frame Data link should exist in nav').toBeGreaterThanOrEqual(0);
  expect(idx2xko, '2XKO Frame Data should appear after FAVCREATORS').toBeGreaterThan(idxFav);
});
