import { test, expect } from '@playwright/test';

test('debug page rendering', async ({ page }) => {
  // Enable console logging
  page.on('console', msg => console.log('BROWSER:', msg.text()));
  
  await page.goto('/index.html');
  
  // Take screenshot immediately
  await page.screenshot({ path: 'test-results/debug-1-initial.png', fullPage: false });
  
  // Wait for network idle
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: 'test-results/debug-2-networkidle.png', fullPage: false });
  
  // Wait some time for React
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'test-results/debug-3-after-3s.png', fullPage: false });
  
  // Wait more for forceBanners
  await page.waitForTimeout(5000);
  await page.screenshot({ path: 'test-results/debug-4-after-8s.png', fullPage: false });
  
  // Check what's on the page - look for the injected container
  const containerExists = await page.locator('#injected-promos').count();
  console.log('Injected Container count:', containerExists);
  
  const promoCount = await page.locator('#injected-promos .promo-banner').count();
  console.log('Promo banners in injected container:', promoCount);
  
  // List all promo elements in the injected container
  const promos = await page.locator('#injected-promos .windows-fixer-promo, #injected-promos .movieshows-promo, #injected-promos .favcreators-promo, #injected-promos .stocks-promo').all();
  console.log('Promo sections found:', promos.length);
  for (const promo of promos) {
    const visible = await promo.isVisible();
    const className = await promo.getAttribute('class');
    console.log('Promo:', className?.split(' ').find(c => c.includes('-promo')), 'visible:', visible);
  }
  
  // Verify all 4 sections exist
  expect(containerExists).toBe(1);
  expect(promos.length).toBe(4);
});
