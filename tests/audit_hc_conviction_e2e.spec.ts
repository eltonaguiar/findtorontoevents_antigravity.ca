/**
 * High Conviction filter — end-to-end (hc_filter v3 + template).
 * Run after hc_filter_rewrite_v2 plan complete + fresh dashboard_data (local or post-GHA deploy).
 *
 *   npx playwright test tests/audit_hc_conviction_e2e.spec.ts --project="Desktop Chrome"
 *
 * Requires: python tools/serve_local.py (Playwright webServer) on 5173.
 * Remote: VERIFY_REMOTE=1 BASE_URL=https://findtorontoevents.ca npx playwright test ...
 */
import { test, expect } from '@playwright/test';

const AUDIT = '/audit/';

const criticalPatterns = [
  'SyntaxError',
  'Unexpected token',
  'ChunkLoadError',
  'denied by modsecurity',
  'Uncaught ',
  'ReferenceError',
];

test.describe('Audit /audit/ — High Conviction (hc_filter v3)', () => {
  test('hero HC enables conviction filter, shows High conviction tag, no critical JS errors', async ({
    page,
  }) => {
    test.setTimeout(120000);
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

    await page.goto(AUDIT, { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForTimeout(3000);

    const hero = page.locator('#btn-conviction-picks-hero');
    await expect(hero, 'HIGH CONVICTION hero button').toBeVisible({ timeout: 20000 });
    await hero.scrollIntoViewIfNeeded();
    await hero.click({ force: true });
    await page.waitForTimeout(500);

    let convictionOn = await page.evaluate(
      () => (window as unknown as { _convictionOnlyFilter?: boolean })._convictionOnlyFilter === true
    );
    if (!convictionOn) {
      convictionOn = await page.evaluate(() => {
        const w = window as unknown as {
          applyHighConvictionPreset?: () => void;
          _convictionOnlyFilter?: boolean;
        };
        w.applyHighConvictionPreset?.();
        return w._convictionOnlyFilter === true;
      });
    }
    expect(convictionOn, '_convictionOnlyFilter should be true after HC (click or applyHighConvictionPreset)').toBe(
      true
    );

    await page.waitForTimeout(2500);
    await expect(page.locator('#tab-active')).toBeVisible();
    await expect(page.locator('.filter-tag').filter({ hasText: /High conviction/i })).toBeVisible({
      timeout: 15000,
    });

    const sandboxTrustCells = await page.evaluate(() => {
      const tab = document.querySelector('#tab-active');
      if (!tab) return -1;
      let n = 0;
      tab.querySelectorAll('table.data-table tbody tr').forEach((row) => {
        row.querySelectorAll('td').forEach((td) => {
          if (td.textContent && td.textContent.trim() === 'SANDBOX') n += 1;
        });
      });
      return n;
    });
    expect(
      sandboxTrustCells,
      'trust-tier cells showing SANDBOX should be 0 when HC filter is on (hc_filter v3 blacklist)'
    ).toBe(0);

    expect(errors, errors.length ? errors.join('\n') : '').toHaveLength(0);
  });
});
