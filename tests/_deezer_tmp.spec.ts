import { test, expect } from '@playwright/test';
test('deezer fetch', async ({ page }) => {
  await page.goto('/weather/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);
  // click songs tab
  await page.click('.player-tab[data-cat="songs"]');
  await page.waitForTimeout(5000);
  const html = await page.locator('#songs-list').innerHTML();
  console.log('SONGS_LIST_HTML:', html.slice(0,500));
});
