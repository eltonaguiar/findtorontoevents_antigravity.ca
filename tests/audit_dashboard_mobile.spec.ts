/**
 * Mobile viewport verification for Unified Audit Dashboard (/audit/).
 * Run: npx playwright test tests/audit_dashboard_mobile.spec.ts
 */
import { test, expect } from '@playwright/test';

const AUDIT_PATH = '/audit/';

const criticalPatterns = [
  'SyntaxError',
  'Unexpected token',
  'ChunkLoadError',
  'Loading chunk',
  'denied by modsecurity',
  'Uncaught ',
  'ReferenceError',
  'TypeError',
];

test.describe('Audit dashboard — mobile viewport', () => {
  test.use({
    viewport: { width: 390, height: 844 },
    hasTouch: true,
  });

  test('loads with zero critical JS errors and core UI visible', async ({ page }) => {
    const errors: string[] = [];

    page.on('pageerror', (err) => {
      if (/Minified React error #418|418.*HTML/.test(err.message)) return;
      errors.push(`PageError: ${err.message}`);
    });

    page.on('console', (msg) => {
      if (msg.type() === 'error' && criticalPatterns.some((p) => msg.text().includes(p))) {
        errors.push(`ConsoleError: ${msg.text()}`);
      }
    });

    await page.goto(AUDIT_PATH, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(3000);

    await expect(page.locator('.header h1')).toBeVisible();
    await expect(page.locator('#filter-bar')).toBeVisible();
    await expect(page.locator('#tab-bar')).toBeVisible();
    await expect(page.locator('.audit-footer-disclaimer')).toBeVisible();

    const scoreTier = page.locator('#f-score-tier');
    const box = await scoreTier.boundingBox();
    expect(box, 'score tier select should have a layout box').toBeTruthy();
    if (box) {
      expect(box.width, 'score tier should not overflow viewport (mobile CSS)').toBeLessThanOrEqual(390);
    }

    expect(
      errors,
      errors.length ? `JS/console errors:\n${errors.join('\n')}` : undefined
    ).toHaveLength(0);
  });
});
