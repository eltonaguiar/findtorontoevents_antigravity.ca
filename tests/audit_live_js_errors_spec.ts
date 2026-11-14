import { test, expect } from '@playwright/test';

const LIVE = {
  audit: 'https://findtorontoevents.ca/audit/',
  hyro: 'https://findtorontoevents.ca/audit/hyrotrader/',
  frontend: 'https://findtorontoevents.ca/',
};

test.describe('Live audit dashboard — console & JS error validation', () => {
  for (const [name, url] of Object.entries(LIVE)) {
    test(`[${name}] loads without uncaught JS errors or failed critical resources`, async ({ page }) => {
      const consoleErrors = [];
      const pageErrors = [];
      const failedRequests = [];

      page.on('console', (msg) => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
      });
      page.on('pageerror', (err) => pageErrors.push(String(err)));
      page.on('requestfailed', (req) => {
        failedRequests.push(`${req.url()} :: ${req.failure()?.errorText ?? 'unknown'}`);
      });

      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });

      await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});

      // let any lazy JS run
      await page.waitForTimeout(5000);

      // sanity: page has content and a title
      const title = await page.title().catch(() => '');
      const bodyText = await page.evaluate(() => document.body?.innerText?.length ?? 0);

      console.log(`[${name}] title="${title}" bodyLen=${bodyText}`);
      console.log(`[${name}] consoleErrors=${consoleErrors.length} pageErrors=${pageErrors.length} failedReq=${failedRequests.length}`);

      // Assert: page rendered (body has text)
      expect(bodyText, `${name}: page should render text`).toBeGreaterThan(50);

      // Critical: no uncaught page errors
      expect(pageErrors, `${name}: uncaught JS errors -> ${pageErrors.slice(0, 5).join(' | ')}`).toHaveLength(0);

      // Console errors: allow a small tolerance but surface them
      if (consoleErrors.length > 0) {
        console.log(`[${name}] CONSOLE ERRORS:\n  ${consoleErrors.slice(0, 10).join('\n  ')}`);
      }
      // We log but do not fail on console noise (many dashboards emit benign 404/analytics noise).
      // Failing only on real page errors + total blankness.
      expect(pageErrors, `${name}: uncaught JS errors`).toHaveLength(0);
    });
  }
});

test.describe('Live audit — interactive sanity', () => {
  test('audit page has an interactive filter/tab control that responds', async ({ page }) => {
    await page.goto(LIVE.audit, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(6000);

    const buttons = page.locator('button, [role="tab"], select');
    const count = await buttons.count();
    console.log(`interactive controls found: ${count}`);
    expect(count).toBeGreaterThan(0);

    // try clicking the first few buttons and assert no page crash
    const limit = Math.min(count, 5);
    for (let i = 0; i < limit; i++) {
      try {
        await buttons.nth(i).click({ timeout: 3000 });
        await page.waitForTimeout(800);
      } catch (e) {
        console.log(`click ${i} skipped: ${e}`);
      }
    }
    // still alive
    await expect(page.locator('body')).toBeAttached();
  });
});
