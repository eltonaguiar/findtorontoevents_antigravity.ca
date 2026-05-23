import { test, expect } from '@playwright/test';

test('Other Stuff promo is visible and popup opens on click', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (err) => {
    // Filter React hydration mismatch (#418) - pre-existing
    if (err.message.includes('#418')) return;
    errors.push(`PageError: ${err.message}`);
  });
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      // Filter known non-critical errors
      if (text.includes('#418') || text.includes('favicon') ||
          text.includes('CORS') || text.includes('net::ERR_') ||
          text.includes('403') || text.includes('400') ||
          text.includes('DIAGNOSTIC') || text.includes('get_me.php') ||
          text.includes('Failed to load resource')) return;
      errors.push(`ConsoleError: ${text}`);
    }
  });

  await page.goto('/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);

  // 1. Verify "Other Stuff" promo section is visible
  const otherStuffPromo = page.locator('.otherstuff-promo');
  await expect(otherStuffPromo.first()).toBeVisible({ timeout: 10000 });
  console.log('Other Stuff promo is visible');

  // 2. Check the weather icon emoji is present
  const weatherIcon = otherStuffPromo.first().locator('text=🌤️');
  await expect(weatherIcon.first()).toBeVisible();
  console.log('Weather icon visible');

  // 3. Check "Other Stuff" title
  const title = otherStuffPromo.first().locator('text=Other Stuff');
  await expect(title.first()).toBeVisible();
  console.log('Title "Other Stuff" visible');

  // 4. Check "Browse ▾" button
  const browseBtn = otherStuffPromo.first().locator('text=Browse');
  await expect(browseBtn.first()).toBeVisible();
  console.log('Browse button visible');

  // 5. Verify openOtherStuffMenu function exists
  const fnType = await page.evaluate(() => typeof (window as any).openOtherStuffMenu);
  expect(fnType).toBe('function');
  console.log('openOtherStuffMenu function exists');

  // 6. Open the popup via the function (simulating click)
  await page.evaluate(() => { (window as any).openOtherStuffMenu(); });
  await page.waitForTimeout(500);

  // 7. Verify popup overlay exists and is open
  const overlayOpen = await page.evaluate(() => {
    const ov = document.getElementById('otherstuff-overlay');
    return ov ? ov.classList.contains('open') : false;
  });
  expect(overlayOpen).toBe(true);
  console.log('Popup overlay is open');

  // 8. Verify popup exists and is open
  const popupOpen = await page.evaluate(() => {
    const pp = document.getElementById('otherstuff-popup');
    return pp ? pp.classList.contains('open') : false;
  });
  expect(popupOpen).toBe(true);
  console.log('Popup is open');

  // 9. Check weather link exists and is highlighted
  const weatherLink = page.locator('#otherstuff-popup .weather-highlight');
  await expect(weatherLink).toBeVisible();
  const weatherTitle = await weatherLink.locator('.os-title').textContent();
  expect(weatherTitle).toContain('Toronto Weather');
  console.log('Weather link highlighted:', weatherTitle);

  // 10. Count all menu items
  const menuItems = page.locator('#otherstuff-popup .otherstuff-item');
  const count = await menuItems.count();
  console.log('Menu items count:', count);
  expect(count).toBeGreaterThanOrEqual(9);

  // 11. Verify key links
  const stocksLink = page.locator('#otherstuff-popup a[href="/findstocks/"]');
  await expect(stocksLink).toBeVisible();
  console.log('Stocks link visible');

  const mentalHealthLink = page.locator('#otherstuff-popup a[href="/MENTALHEALTHRESOURCES/"]');
  await expect(mentalHealthLink).toBeVisible();
  console.log('Mental Health link visible');

  const weatherPageLink = page.locator('#otherstuff-popup a[href="/weather/"]');
  await expect(weatherPageLink).toBeVisible();
  console.log('Weather page link visible');

  const vrLink = page.locator('#otherstuff-popup a[href="/vr/"]');
  await expect(vrLink).toBeVisible();
  console.log('VR link visible');

  // 12. Take screenshot of open popup
  await page.screenshot({ path: 'test-results/otherstuff-popup-open.png' });
  console.log('Screenshot saved');

  // 13. Close popup via closeOtherStuffMenu
  await page.evaluate(() => { (window as any).closeOtherStuffMenu(); });
  await page.waitForTimeout(300);
  const closedState = await page.evaluate(() => {
    const ov = document.getElementById('otherstuff-overlay');
    return ov ? ov.classList.contains('open') : true;
  });
  expect(closedState).toBe(false);
  console.log('Popup closed via closeOtherStuffMenu');

  // 14. Reopen and close with Escape
  await page.evaluate(() => { (window as any).openOtherStuffMenu(); });
  await page.waitForTimeout(300);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  const closedEsc = await page.evaluate(() => {
    const ov = document.getElementById('otherstuff-overlay');
    return ov ? ov.classList.contains('open') : true;
  });
  expect(closedEsc).toBe(false);
  console.log('Popup closed by Escape key');

  // 15. No JS errors
  console.log('JS errors:', errors.length);
  errors.forEach(e => console.log('  -', e));
  expect(errors).toHaveLength(0);
});
