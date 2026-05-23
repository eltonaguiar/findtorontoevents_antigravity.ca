import { test, expect } from '@playwright/test';

test('audit dashboard loads + no JS console errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(`pageerror: ${e.message}`));
  page.on('console', m => {
    if (m.type() === 'error') errors.push(`console.error: ${m.text()}`);
  });
  await page.goto('https://findtorontoevents.ca/audit/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await expect(page.locator('text=/MAJOR GOAL|asset.class|hedge.fund.grade/i').first()).toBeVisible({ timeout: 30000 });
  // SPORTS should not appear in asset-class dropdown after PR-A lands. Grep test (pre-merge will still see SPORTS).
  const html = await page.content();
  const sportsCount = (html.match(/SPORTS/g) || []).length;
  console.log(`SPORTS references in HTML: ${sportsCount}`);
  console.log(`JS errors: ${errors.length}`);
  if (errors.length) console.log(errors.join('\n'));
  expect(errors).toEqual([]);
});
