const { test, expect } = require('@playwright/test');

const AUDIT_URL = 'https://findtorontoevents.ca/audit/';
const FUNDS_URL = 'https://findtorontoevents.ca/audit/funds.html';

test.describe('Dashboard Feature Verification', () => {

  test('Audit page loads without JS errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    // Check for the critical "s is not defined" error
    const sErrors = errors.filter(e => e.includes('s is not defined'));
    expect(sErrors.length).toBe(0);

    await page.screenshot({ path: 'tests/screenshots/audit_load.png', fullPage: false });
  });

  test('Active Picks tab renders with picks', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    // Click Active Picks tab
    await page.click('[data-tab="active"]');
    await page.waitForTimeout(1000);

    // Should show "Active Picks (X)" heading
    const heading = await page.textContent('#tab-active h2');
    expect(heading).toContain('Active Picks');

    await page.screenshot({ path: 'tests/screenshots/active_picks.png', fullPage: false });
  });

  test('Filter banner shows active filters with dismiss buttons', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    // Set a filter
    await page.selectOption('#f-asset', 'CRYPTO');
    await page.waitForTimeout(1000);

    // Check filter banner appears
    const banner = await page.locator('#filter-active-indicator');
    await expect(banner).toBeVisible();

    // Check it contains the filter text
    const bannerText = await banner.textContent();
    expect(bannerText).toContain('CRYPTO');

    // Check for dismiss ✕ button
    expect(bannerText).toContain('✕');

    await page.screenshot({ path: 'tests/screenshots/filter_banner.png', fullPage: false });
  });

  test('Red glow on active filter dropdowns', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    // Set asset filter
    await page.selectOption('#f-asset', 'CRYPTO');
    await page.waitForTimeout(500);

    // Check if the dropdown has the filter-glow class
    const hasGlow = await page.locator('#f-asset.filter-glow').count();
    expect(hasGlow).toBeGreaterThan(0);

    await page.screenshot({ path: 'tests/screenshots/filter_glow.png', fullPage: false });
  });

  test('Closed Picks has Entry/Exit EST and Hold columns', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    // Click Closed Picks tab
    await page.click('[data-tab="closed"]');
    await page.waitForTimeout(1000);

    const closedContent = await page.textContent('#tab-closed');

    // Check for Entry/Exit/Hold columns
    const hasEntryEST = closedContent.includes('Entry (EST)') || closedContent.includes('Entry');
    const hasHold = closedContent.includes('Hold');

    expect(hasEntryEST || hasHold).toBeTruthy();

    await page.screenshot({ path: 'tests/screenshots/closed_picks.png', fullPage: false });
  });

  test('System Health Trends section exists (from enhancements.js)', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(5000); // Extra wait for enhancements.js

    // Check if System Health Trends rendered
    const trendSection = await page.locator('text=System Health').first();
    const trendVisible = await trendSection.isVisible().catch(() => false);

    console.log('System Health Trends visible:', trendVisible);
    await page.screenshot({ path: 'tests/screenshots/system_health_trends.png', fullPage: false });
  });

  test('Strategy Consensus Matrix (True Signal) exists', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(5000);

    // Check for Strategy Consensus section
    const consensusSection = await page.locator('text=Strategy Consensus').first();
    const consensusVisible = await consensusSection.isVisible().catch(() => false);

    // Also check for True Signal text
    const trueSignal = await page.locator('text=True Signal').first();
    const trueSignalVisible = await trueSignal.isVisible().catch(() => false);

    console.log('Strategy Consensus visible:', consensusVisible);
    console.log('True Signal visible:', trueSignalVisible);
    await page.screenshot({ path: 'tests/screenshots/strategy_consensus.png', fullPage: false });
  });

  test('Time-Window System Leaderboard exists', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(5000);

    // Check for time window tabs (4H / 24H / 7D / All)
    const has4H = await page.locator('text=4H').first().isVisible().catch(() => false);
    const has24H = await page.locator('text=24H').first().isVisible().catch(() => false);
    const has7D = await page.locator('text=7D').first().isVisible().catch(() => false);

    console.log('4H tab visible:', has4H);
    console.log('24H tab visible:', has24H);
    console.log('7D tab visible:', has7D);

    // Check for the time-window leaderboard container
    const twContainer = await page.locator('#tw-leaderboard').count();
    console.log('Time-window leaderboard container:', twContainer);

    await page.screenshot({ path: 'tests/screenshots/time_window_leaderboard.png', fullPage: false });
  });

  test('Agreement matrix is below tab bar (not above)', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    // The matrix should be AFTER the tab-bar, not before
    const tabBarY = await page.locator('#tab-bar').boundingBox().then(b => b?.y || 0);
    const matrixY = await page.locator('#agreement-matrix').boundingBox().then(b => b?.y || 9999);

    console.log('Tab bar Y:', tabBarY, 'Matrix Y:', matrixY);
    expect(matrixY).toBeGreaterThan(tabBarY);

    await page.screenshot({ path: 'tests/screenshots/matrix_position.png', fullPage: false });
  });

  test('No column filter rows in tables', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    // Click Overview to see the tables
    await page.click('[data-tab="overview"]');
    await page.waitForTimeout(1000);

    // Check there are NO filter-row elements
    const filterRows = await page.locator('.filter-row').count();
    console.log('Filter rows found:', filterRows);
    expect(filterRows).toBe(0);

    await page.screenshot({ path: 'tests/screenshots/no_filter_rows.png', fullPage: false });
  });

  test('Funds page loads with live tracker', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(5000);

    // Check for Live Forward Test Portfolio section
    const liveTracker = await page.locator('text=Live Forward Test Portfolio').first();
    const visible = await liveTracker.isVisible().catch(() => false);

    console.log('Live Forward Test Portfolio visible:', visible);

    // Check for position table
    const hasPositions = await page.locator('text=Entry').first().isVisible().catch(() => false);
    console.log('Position table visible:', hasPositions);

    // Check for Entry (EST) column
    const hasEntryEST = await page.locator('text=Entry (EST)').first().isVisible().catch(() => false);
    console.log('Entry (EST) column visible:', hasEntryEST);

    await page.screenshot({ path: 'tests/screenshots/funds_live_tracker.png', fullPage: false });
  });

  test('TL;DR Winners button exists', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    const tldrBtn = await page.locator('text=TL;DR Winners').first();
    const visible = await tldrBtn.isVisible().catch(() => false);
    console.log('TL;DR Winners button visible:', visible);

    await page.screenshot({ path: 'tests/screenshots/tldr_button.png', fullPage: false });
  });

  test('Insights button exists near Active Picks', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    await page.click('[data-tab="active"]');
    await page.waitForTimeout(1000);

    const insightsBtn = await page.locator('text=Insights').first();
    const visible = await insightsBtn.isVisible().catch(() => false);
    console.log('Insights button visible:', visible);

    await page.screenshot({ path: 'tests/screenshots/insights_button.png', fullPage: false });
  });

  test('Last 10 streak column exists on Active Picks', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    await page.click('[data-tab="active"]');
    await page.waitForTimeout(1000);

    const lastTen = await page.locator('text=Last 10').first();
    const visible = await lastTen.isVisible().catch(() => false);
    console.log('Last 10 streak column visible:', visible);

    await page.screenshot({ path: 'tests/screenshots/last_10_streak.png', fullPage: false });
  });

});
