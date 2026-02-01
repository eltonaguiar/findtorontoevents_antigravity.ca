/**
 * Inspect Quick Nav link order (FAVCREATORS, Mental Health, 2XKO).
 * Run: npx playwright test tests/inspect_quick_nav_order.spec.ts
 */
import { test, expect } from '@playwright/test';

const BASE = process.env.BASE_URL || 'http://localhost:5173';

test('inspect Quick Nav link order and assert Mental Health below FAVCREATORS', async ({
  page,
}) => {
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.getByTitle('Quick Navigation').click();
  await page.waitForTimeout(800);

  const nav = page.locator('nav');
  await expect(nav).toBeVisible();

  const links = nav.locator('a[href]');
  const items: { text: string; href: string; index: number }[] = [];
  const count = await links.count();
  for (let i = 0; i < count; i++) {
    const href = await links.nth(i).getAttribute('href');
    const text = (await links.nth(i).textContent())?.trim() ?? '';
    if (href) items.push({ text, href, index: i });
  }

  const idxFav = items.findIndex((x) => x.text.includes('FAVCREATORS'));
  const idxMental = items.findIndex((x) => x.text.includes('Mental Health'));
  const idx2xko = items.findIndex((x) => x.text.includes('2XKO Frame Data'));

  console.log(
    'Quick Nav link order:',
    items.map((x) => `${x.index}: ${x.text} (${x.href})`).join(' | ')
  );
  console.log('FAVCREATORS index:', idxFav, '| Mental Health index:', idxMental, '| 2XKO index:', idx2xko);

  expect(idxFav, 'FAVCREATORS link should exist').toBeGreaterThanOrEqual(0);
  expect(idxMental, 'Mental Health Resources link should exist').toBeGreaterThanOrEqual(0);
  expect(idx2xko, '2XKO Frame Data link should exist').toBeGreaterThanOrEqual(0);

  expect(
    idxMental,
    'Mental Health Resources must appear after FAVCREATORS. Order: ' +
      items.map((x) => x.text).join(' -> ')
  ).toBeGreaterThan(idxFav);

  expect(
    idx2xko,
    '2XKO Frame Data must appear after Mental Health. Order: ' +
      items.map((x) => x.text).join(' -> ')
  ).toBeGreaterThan(idxMental);
});
