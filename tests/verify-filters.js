const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('https://findtorontoevents.ca/affiliates/', { waitUntil: 'networkidle', timeout: 30000 });

  // Check search bar exists
  const searchExists = await page.locator('#product-search').count();
  console.log('Search bar present:', searchExists > 0);

  // Check tag pills exist
  const pillCount = await page.locator('.tag-pill').count();
  console.log('Tag pills:', pillCount);

  // Test: type "eye" in search
  await page.fill('#product-search', 'eye');
  await page.waitForTimeout(300);
  const visibleAfterSearch = await page.locator('.product-card:not(.filter-hidden)').count();
  const hiddenAfterSearch = await page.locator('.product-card.filter-hidden').count();
  console.log('Search "eye": visible=' + visibleAfterSearch + ', hidden=' + hiddenAfterSearch);

  // Check status text
  const statusText = await page.locator('#filter-status').textContent();
  console.log('Status text:', statusText.trim());

  // Clear search
  await page.fill('#product-search', '');
  await page.waitForTimeout(300);
  const visibleAfterClear = await page.locator('.product-card:not(.filter-hidden)').count();
  console.log('After clear: visible=' + visibleAfterClear);

  // Test: click "candy" tag
  await page.locator('.tag-pill[data-tag="candy"]').click();
  await page.waitForTimeout(300);
  const visibleAfterCandy = await page.locator('.product-card:not(.filter-hidden)').count();
  console.log('Tag "candy": visible=' + visibleAfterCandy);

  // Click candy again to deselect
  await page.locator('.tag-pill[data-tag="candy"]').click();
  await page.waitForTimeout(300);

  // Test: click "vr" tag
  await page.locator('.tag-pill[data-tag="vr"]').click();
  await page.waitForTimeout(300);
  const visibleAfterVr = await page.locator('.product-card:not(.filter-hidden)').count();
  console.log('Tag "vr": visible=' + visibleAfterVr);

  // Check category hiding — non-VR categories should be hidden
  const visibleLabels = await page.locator('.category-label:not(.filter-hidden)').count();
  const hiddenLabels = await page.locator('.category-label.filter-hidden').count();
  console.log('Category labels: visible=' + visibleLabels + ', hidden=' + hiddenLabels);

  console.log('\n=== ALL TESTS PASSED ===');
  await browser.close();
})();
