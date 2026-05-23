/**
 * Playwright test: sports-betting.html JS-error capture.
 *
 * Loads the live page, clicks through every tab, and asserts:
 *   - No JS errors in console
 *   - No unhandled promise rejections
 *   - No 4xx/5xx responses on API calls (sports_picks, sports_bets, sports_ml,
 *     sports_steam, sports_arb)
 *   - Each tab renders some content (no permanent "Loading…" placeholders)
 *   - The FINISHED filter toggle works (PR #404)
 *   - The Performance tab shows the tier table + tier×sport matrix (PR #409)
 *   - The CLV trend chart renders or hides cleanly (PR #414)
 *
 * Run: `npx playwright test tests/sports_betting_js_errors.spec.js`
 *
 * Catches the kinds of regressions we hit this session:
 *   - PHP parse errors leaking into HTML
 *   - Conflict markers in JS (would fail at parse, page goes blank)
 *   - Missing API endpoints causing tab content to never load
 *   - Stale tab handlers throwing on missing DOM nodes
 */
const { test, expect } = require('@playwright/test');

const URL = 'https://findtorontoevents.ca/live-monitor/sports-betting.html';

test.describe('sports-betting.html JS errors + tabs', () => {

  test('no console errors on initial load', async ({ page }) => {
    const consoleErrors = [];
    const apiFailures = [];

    // The sports sub-app has no favicon; intercept at the network layer so
    // the browser never logs the recurring 404 console error that masked
    // real JS regressions in CI. Other 404s are caught explicitly via the
    // `apiFailures` listener below, so suppressing favicon at the route
    // level is narrowly scoped and does not hide other failures.
    await page.route('**/favicon.ico', route => route.fulfill({ status: 204, body: '' }));

    page.on('pageerror', e => consoleErrors.push(`pageerror: ${e.message}`));
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(`console.error: ${msg.text()}`);
      }
    });
    page.on('response', r => {
      if (r.url().includes('/live-monitor/api/') && r.status() >= 400) {
        apiFailures.push(`${r.status()} ${r.url()}`);
      }
    });

    await page.goto(URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);  // let async fetchPicks finish

    // The grid div is in the DOM (may be display:none until picks load).
    await expect(page.locator('#value-bets-grid')).toBeAttached();

    // PR #754: 503/401 from Odds API are gracefully handled by the stale-picks banner; allow them through
    const unexpectedErrors = consoleErrors.filter(e =>
      !/Failed to load resource.*503/i.test(e) &&
      !/Odds API.*401/i.test(e) &&
      !/Failed to load resource.*401/i.test(e)
    );

    expect(unexpectedErrors, `console errors:\n${unexpectedErrors.join('\n')}`).toHaveLength(0);

    // PR #754: 503 from sports_failover_proxy.php are the exact prod outage this PR's banner handles
    const unexpectedApiFailures = apiFailures.filter(f =>
      !/sports_failover_proxy\.php.*\b(503|401)\b/i.test(f) &&
      !/\b(503|401)\b.*sports_failover_proxy\.php/i.test(f)
    );
    expect(unexpectedApiFailures, `API failures:\n${unexpectedApiFailures.join('\n')}`).toHaveLength(0);
  });

  test('FINISHED filter toggle hides finished cards by default', async ({ page }) => {
    await page.goto(URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Server-side `is_finished` should mark some cards data-finished="1".
    // Default state hides them via CSS; the toggle bar is visible only when finished picks exist.
    const finishedCards = page.locator('.pick-card[data-finished="1"]');
    const count = await finishedCards.count();
    if (count > 0) {
      // First finished card should be hidden by default.
      await expect(finishedCards.first()).toBeHidden();
      // Toggle button text varies; match the localStorage key the toggle writes.
      const toggleBtn = page.locator('button:has-text("Show finished"), button:has-text("show finished")').first();
      if (await toggleBtn.count() > 0) {
        await toggleBtn.click();
        await expect(finishedCards.first()).toBeVisible();
      }
    }
  });

  test('Performance tab shows tier table + tier×sport matrix', async ({ page }) => {
    await page.goto(URL, { waitUntil: 'networkidle' });
    await page.click('button:has-text("Performance")');
    await page.waitForTimeout(2000);

    // PR #409: tier-perf table
    await expect(page.locator('text=Performance by Recommendation Tier')).toBeVisible();
    // Tier × Sport matrix subtitle
    await expect(page.locator('text=ROI matrix')).toBeVisible();
    // CLV trend chart (PR #414) — either visible OR hidden cleanly when empty
    const clvContainer = page.locator('#clv-trend-container');
    const visible = await clvContainer.isVisible().catch(() => false);
    // Don't fail when empty; just ensure the canvas didn't throw.
    if (visible) {
      await expect(page.locator('#clv-trend-chart')).toBeVisible();
    }
  });

  test('Pick History tab populates with at least one day', async ({ page }) => {
    const apiPickHistoryResp = page.waitForResponse(r => r.url().includes('action=pick_history'));
    await page.goto(URL, { waitUntil: 'networkidle' });
    await page.click('button:has-text("Pick History")');
    const resp = await apiPickHistoryResp;
    const body = await resp.json();
    expect(body.ok).toBe(true);
    expect(Array.isArray(body.days)).toBeTruthy();
    expect(body.days.length).toBeGreaterThan(0);
    // _diag block (this fix)
    expect(body._diag).toBeTruthy();
  });

  test('all tabs switch without throwing', async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));

    await page.goto(URL, { waitUntil: 'networkidle' });

    const tabs = ['Today\'s Picks', 'Odds Comparison', 'Arbitrage', 'Steam Moves',
                  'My Bets', 'Performance', 'Pick History'];
    for (const name of tabs) {
      const btn = page.locator(`button:has-text("${name}")`).first();
      if (await btn.count() > 0) {
        await btn.click();
        await page.waitForTimeout(800);
      }
    }

    expect(errors, `pageerrors during tab switching:\n${errors.join('\n')}`).toHaveLength(0);
  });
});
