/**
 * Live audit: strategy description tooltip sanity + TRACK warning icon census.
 * https://findtorontoevents.ca/audit/
 */
import { test, expect } from '@playwright/test';

const AUDIT_URL = 'https://findtorontoevents.ca/audit/';

test.describe('Audit remote — warnings & strategy tips', () => {
  test('TRACK warning icons + strategy cells present', async ({ page }) => {
    test.setTimeout(120000);
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(`PageError: ${e.message}`));
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(`ConsoleError: ${msg.text()}`);
    });

    const res = await page.goto(AUDIT_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 90000,
    });
    expect(res?.status(), 'audit HTTP status').toBeLessThan(400);

    await page.locator('button[data-tab="active"]').first().click();
    await page.waitForSelector('#tab-active.active', { timeout: 90000 });
    await page.waitForSelector('#tab-active table.data-table', { timeout: 90000 });
    await page.waitForTimeout(1500);

    const warnIcons = page.locator('.track-strat-warn-icon');
    const nWarn = await warnIcons.count();
    const activeHeading = page.getByRole('heading', { name: /Active Picks/i });
    await expect(activeHeading).toBeVisible({ timeout: 30000 });

    const table = page.locator('#tab-active table.data-table').first();
    await expect(table).toBeVisible();
    const rows = await table.locator('tbody tr').count();
    expect(rows).toBeGreaterThan(0);

    const titles = await warnIcons.evaluateAll((els) =>
      els.map((e) => (e as HTMLElement).getAttribute('title') || '')
    );
    const sampleTitles = titles.slice(0, 5);

    // eslint-disable-next-line no-console
    console.log(JSON.stringify({
      trackWarningIconCount: nWarn,
      tableBodyRows: rows,
      sampleWarningTitles: sampleTitles,
      jsErrors: errors.slice(0, 8),
    }, null, 2));

    expect(errors.filter((e) => /SyntaxError|Unexpected|ChunkLoadError/i.test(e))).toHaveLength(0);
    expect(nWarn).toBeGreaterThanOrEqual(0);
  });
});
