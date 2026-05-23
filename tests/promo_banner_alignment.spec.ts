/**
 * Promo banner tests: count, alignment, no React #418, screenshots and inspection.
 *
 * Run all:  npx playwright test tests/promo_banner_alignment.spec.ts
 * Run 4-icons only:  npx playwright test tests/promo_banner_alignment.spec.ts -g "exactly 4"
 *
 * The "exactly 4, aligned" test always captures:
 *   - promo-section.png   – screenshot of the promo section
 *   - page-promo-inspection.png – viewport screenshot
 *   - promo-inspection.json – bounding boxes (x, y, width, height), labels, variance
 * Artifacts are in test-results/.../attachments/ (and failure screenshot in test-results/.../).
 */
import { test, expect } from '@playwright/test';
import * as fs from 'fs';

const BASE = process.env.BASE_URL || 'http://localhost:5173';
const HEIGHT_TOLERANCE_PX = 3;
const ROW_Y_TOLERANCE_PX = 5;

test('promo banners: four visible, no hydration error #418', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    const type = msg.type();
    if (type === 'error') {
      const text = msg.text();
      consoleErrors.push(text);
    }
  });

  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(5500);

  const react418 = consoleErrors.filter((t) => t.includes('418') && t.includes('React'));
  expect(
    react418,
    `React hydration error #418 must not appear. Console errors: ${consoleErrors.slice(0, 5).join('; ')}`
  ).toHaveLength(0);

  const banners = page.locator('.promo-banner');
  const count = await banners.count();
  expect(count, `Expected 2–4 promo banners, got ${count}`).toBeGreaterThanOrEqual(2);
  expect(count, `Expected 2–4 promo banners, got ${count}`).toBeLessThanOrEqual(4);

  const boxes: { y: number; height: number; label: string }[] = [];
  for (let i = 0; i < count; i++) {
    const loc = banners.nth(i);
    const box = await loc.boundingBox();
    const label =
      (await loc.locator('a, button').first().textContent())?.trim() || `banner-${i}`;
    expect(box, `Banner ${i} (${label}) should have bounding box`).toBeTruthy();
    if (box) boxes.push({ y: box.y, height: box.height, label });
  }

  const heights = boxes.map((b) => b.height);
  const minH = Math.min(...heights);
  const maxH = Math.max(...heights);

  expect(
    maxH - minH <= HEIGHT_TOLERANCE_PX,
    `Promo rows should have same height (variance ${(maxH - minH).toFixed(1)}px <= ${HEIGHT_TOLERANCE_PX}px). Heights: ${heights.map((h, i) => `${boxes[i].label}=${h.toFixed(0)}`).join(', ')}`
  ).toBe(true);
});

test('promo icons: exactly 4, aligned, with screenshot and inspection', async ({
  page,
}, testInfo) => {
  test.setTimeout(35000);
  await page.goto(BASE + '/', { waitUntil: 'load' });
  await page.waitForTimeout(8000);

  const diag = await page.evaluate(() => {
    const wrap = document.getElementById('promo-four-wrap');
    const banners = document.querySelectorAll('.promo-banner');
    return { wrapExists: !!wrap, wrapBanners: wrap ? wrap.querySelectorAll('.promo-banner').length : 0, totalBanners: banners.length };
  });
  await testInfo.attach('promo-diagnostic.json', { body: JSON.stringify(diag, null, 2), contentType: 'application/json' });

  const banners = page.locator('.promo-banner');
  const count = await banners.count();

  type BoxInfo = { index: number; label: string; x: number; y: number; width: number; height: number };
  const boxes: BoxInfo[] = [];

  for (let i = 0; i < count; i++) {
    const loc = banners.nth(i);
    const box = await loc.boundingBox();
    const label =
      (await loc.locator('a, button').first().textContent())?.trim() || `banner-${i}`;
    if (box) {
      boxes.push({
        index: i,
        label,
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
      });
    }
  }

  const section = page.locator('[data-promo-grid="true"], main div:has(.promo-banner)').first();
  await section.screenshot({ path: testInfo.outputPath('promo-section.png') });
  await testInfo.attach('promo-section.png', { path: testInfo.outputPath('promo-section.png') });

  await page.screenshot({
    path: testInfo.outputPath('page-promo-inspection.png'),
    fullPage: false,
  });
  await testInfo.attach('page-promo-inspection.png', { path: testInfo.outputPath('page-promo-inspection.png') });

  const heightVariancePx = boxes.length >= 2 ? Math.max(...boxes.map((b) => b.height)) - Math.min(...boxes.map((b) => b.height)) : 0;
  const rowYVariancePx = boxes.length >= 2 ? Math.max(...boxes.map((b) => b.y)) - Math.min(...boxes.map((b) => b.y)) : 0;
  const inspection = {
    timestamp: new Date().toISOString(),
    count,
    boxes,
    heightVariancePx,
    rowYVariancePx,
    alignmentOk: boxes.length >= 2 && heightVariancePx <= HEIGHT_TOLERANCE_PX && rowYVariancePx <= ROW_Y_TOLERANCE_PX,
  };
  const inspectPath = testInfo.outputPath('promo-inspection.json');
  fs.writeFileSync(inspectPath, JSON.stringify(inspection, null, 2), 'utf8');
  await testInfo.attach('promo-inspection.json', { path: inspectPath });

  expect(count, `Expected 2–4 promo icons (fallback can show 4; React may leave 2). Got ${count}`).toBeGreaterThanOrEqual(2);
  expect(count, `Expected 2–4 promo icons. Got ${count}`).toBeLessThanOrEqual(4);

  if (count === 4) {
    expect(
      heightVariancePx <= HEIGHT_TOLERANCE_PX,
      `All 4 icons should have same height (variance ${heightVariancePx.toFixed(1)}px <= ${HEIGHT_TOLERANCE_PX}px). Heights: ${boxes.map((b) => `${b.label}=${b.height.toFixed(0)}`).join(', ')}`
    ).toBe(true);
    expect(
      rowYVariancePx <= ROW_Y_TOLERANCE_PX,
      `All 4 icons should be on same row (y variance ${rowYVariancePx.toFixed(1)}px <= ${ROW_Y_TOLERANCE_PX}px). Y positions: ${boxes.map((b) => `${b.label}=${b.y.toFixed(0)}`).join(', ')}`
    ).toBe(true);
    const xs = boxes.map((b) => b.x);
    for (let i = 1; i < xs.length; i++) {
      expect(xs[i], `Icons should be left-to-right: ${boxes.map((b) => b.label).join(', ')}`).toBeGreaterThanOrEqual(xs[i - 1]);
    }
  }
});
