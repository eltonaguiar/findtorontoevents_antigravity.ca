/**
 * Inspect Quick Nav link order (FAVCREATORS, Mental Health, VR, Accountability).
 * Run: npx playwright test tests/inspect_quick_nav_order.spec.ts
 */
import { test, expect } from '@playwright/test';

const BASE = process.env.BASE_URL || 'http://localhost:5173';

test('inspect Quick Nav link order and assert correct ordering', async ({
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
  const idxVR = items.findIndex((x) => x.text.includes('VR Experience'));
  const idxVRMobile = items.findIndex((x) => x.text.includes('VR Mobile'));
  const idxAccountability = items.findIndex((x) => x.text.includes('Accountability Dashboard'));

  console.log(
    'Quick Nav link order:',
    items.map((x) => `${x.index}: ${x.text} (${x.href})`).join(' | ')
  );
  console.log(
    'FAVCREATORS index:', idxFav,
    '| Mental Health index:', idxMental,
    '| VR Experience index:', idxVR,
    '| VR Mobile index:', idxVRMobile,
    '| Accountability index:', idxAccountability
  );

  // All required links must exist
  expect(idxFav, 'FAVCREATORS link should exist').toBeGreaterThanOrEqual(0);
  expect(idxMental, 'Mental Health Resources link should exist').toBeGreaterThanOrEqual(0);
  expect(idxVR, 'VR Experience link should exist').toBeGreaterThanOrEqual(0);
  expect(idxVRMobile, 'VR Mobile link should exist').toBeGreaterThanOrEqual(0);
  expect(idxAccountability, 'Accountability Dashboard link should exist').toBeGreaterThanOrEqual(0);

  // 2XKO should NOT exist (removed)
  const idx2xko = items.findIndex((x) => x.text.includes('2XKO Frame Data'));
  expect(idx2xko, '2XKO Frame Data should be removed').toBe(-1);

  // Ordering: FAVCREATORS < Mental Health < VR < VR Mobile < Accountability
  expect(
    idxMental,
    'Mental Health Resources must appear after FAVCREATORS'
  ).toBeGreaterThan(idxFav);

  expect(
    idxVR,
    'VR Experience must appear after Mental Health'
  ).toBeGreaterThan(idxMental);

  expect(
    idxVRMobile,
    'VR Mobile must appear after VR Experience'
  ).toBeGreaterThan(idxVR);

  expect(
    idxAccountability,
    'Accountability Dashboard must appear after VR Mobile'
  ).toBeGreaterThan(idxVRMobile);
});
