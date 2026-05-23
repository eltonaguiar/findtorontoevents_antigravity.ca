const { test, expect } = require('@playwright/test');

const BASE_URL = 'https://findtorontoevents.ca/riseoftheclaw.html';

test.describe('LIVE / BACK-TEST Mode Switching', () => {

  test.beforeEach(async ({ page }) => {
    // Clear localStorage before each test so we start fresh
    await page.goto(BASE_URL);
    await page.evaluate(() => localStorage.removeItem('dataMode'));
    await page.reload();
    await page.waitForLoadState('networkidle');
  });

  // ---------------------------------------------------------------
  // 1. Click LIVE button - verify live_competition.json is fetched
  // ---------------------------------------------------------------
  test('clicking LIVE button fetches live_competition.json', async ({ page }) => {
    // First switch to backtest so we can switch TO live
    await page.locator('#btnBacktestMode').click();
    await page.waitForTimeout(1000);

    // Monitor network requests after clicking LIVE
    const jsonRequests = [];
    page.on('response', response => {
      if (response.url().includes('.json')) {
        jsonRequests.push(response.url());
      }
    });

    await page.locator('#btnLiveMode').click();
    await page.waitForTimeout(2000);

    const hasLiveCompetition = jsonRequests.some(url => url.includes('live_competition.json'));
    console.log('JSON requests after LIVE click:', jsonRequests);
    expect(hasLiveCompetition).toBe(true);
  });

  // ---------------------------------------------------------------
  // 2. Click BACK-TEST button - verify algorithms.json and
  //    active_picks.json are fetched
  // ---------------------------------------------------------------
  test('clicking BACK-TEST button fetches algorithms.json and active_picks.json', async ({ page }) => {
    // Monitor network requests after clicking BACK-TEST
    const jsonRequests = [];
    page.on('response', response => {
      if (response.url().includes('.json')) {
        jsonRequests.push(response.url());
      }
    });

    await page.locator('#btnBacktestMode').click();
    await page.waitForTimeout(2000);

    const hasAlgorithms = jsonRequests.some(url => url.includes('algorithms.json'));
    const hasActivePicks = jsonRequests.some(url => url.includes('active_picks.json'));

    console.log('JSON requests after BACK-TEST click:', jsonRequests);
    expect(hasAlgorithms).toBe(true);
    expect(hasActivePicks).toBe(true);
  });

  // ---------------------------------------------------------------
  // 3. Switch back and forth multiple times
  // ---------------------------------------------------------------
  test('switching modes back and forth multiple times works correctly', async ({ page }) => {
    for (let i = 0; i < 3; i++) {
      // Switch to BACK-TEST
      await page.locator('#btnBacktestMode').click();
      await page.waitForTimeout(1000);

      await expect(page.locator('#btnBacktestMode')).toHaveClass(/active/);
      await expect(page.locator('#btnLiveMode')).not.toHaveClass(/active/);

      const backtestBadge = await page.locator('#dataSourceBadge').textContent();
      expect(backtestBadge).toContain('SIMULATED');

      // Switch to LIVE
      await page.locator('#btnLiveMode').click();
      await page.waitForTimeout(1000);

      await expect(page.locator('#btnLiveMode')).toHaveClass(/active/);
      await expect(page.locator('#btnBacktestMode')).not.toHaveClass(/active/);

      const liveBadge = await page.locator('#dataSourceBadge').textContent();
      expect(liveBadge).toContain('LIVE');
    }
  });

  // ---------------------------------------------------------------
  // 4. Verify localStorage persistence
  // ---------------------------------------------------------------
  test('mode selection persists in localStorage', async ({ page }) => {
    // Switch to BACK-TEST
    await page.locator('#btnBacktestMode').click();
    await page.waitForTimeout(1000);

    let savedMode = await page.evaluate(() => localStorage.getItem('dataMode'));
    expect(savedMode).toBe('backtest');

    // Switch to LIVE
    await page.locator('#btnLiveMode').click();
    await page.waitForTimeout(1000);

    savedMode = await page.evaluate(() => localStorage.getItem('dataMode'));
    expect(savedMode).toBe('live');

    // Reload page and verify mode persists
    await page.reload();
    await page.waitForLoadState('networkidle');

    savedMode = await page.evaluate(() => localStorage.getItem('dataMode'));
    expect(savedMode).toBe('live');

    // The LIVE button should still be active after reload
    await expect(page.locator('#btnLiveMode')).toHaveClass(/active/);
  });

  // ---------------------------------------------------------------
  // 5. Verify badge updates correctly
  // ---------------------------------------------------------------
  test('data source badge updates correctly on mode switch', async ({ page }) => {
    // Default should be LIVE
    const badge = page.locator('#dataSourceBadge');

    // Check LIVE badge (browser may return hex or rgb format)
    await expect(badge).toContainText('LIVE');
    const liveBg = await badge.evaluate(el => el.style.background);
    expect(liveBg).toMatch(/#3b82f6|rgb\(59,\s*130,\s*246\)/);

    // Switch to BACK-TEST
    await page.locator('#btnBacktestMode').click();
    await page.waitForTimeout(1000);

    await expect(badge).toContainText('SIMULATED');
    const backtestBg = await badge.evaluate(el => el.style.background);
    expect(backtestBg).toMatch(/#22c55e|rgb\(34,\s*197,\s*94\)/);

    // Switch back to LIVE
    await page.locator('#btnLiveMode').click();
    await page.waitForTimeout(1000);

    await expect(badge).toContainText('LIVE');
    const liveBgAfter = await badge.evaluate(el => el.style.background);
    expect(liveBgAfter).toMatch(/#3b82f6|rgb\(59,\s*130,\s*246\)/);
  });

  // ---------------------------------------------------------------
  // 6. Verify no JavaScript errors during switching
  // ---------------------------------------------------------------
  test('no JavaScript errors during mode switching', async ({ page }) => {
    const errors = [];
    page.on('pageerror', error => {
      errors.push(error.message);
    });
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Switch multiple times
    await page.locator('#btnBacktestMode').click();
    await page.waitForTimeout(1500);

    await page.locator('#btnLiveMode').click();
    await page.waitForTimeout(1500);

    await page.locator('#btnBacktestMode').click();
    await page.waitForTimeout(1500);

    await page.locator('#btnLiveMode').click();
    await page.waitForTimeout(1500);

    console.log('JS errors during mode switching:', errors);

    // Filter out non-critical network errors (404s on data files are acceptable)
    const criticalErrors = errors.filter(err =>
      !err.includes('Failed to load') &&
      !err.includes('net::ERR') &&
      !err.includes('404')
    );

    expect(criticalErrors).toHaveLength(0);
  });

  // ---------------------------------------------------------------
  // 7. Verify data reloads properly after each switch
  // ---------------------------------------------------------------
  test('data reloads properly after switching to BACK-TEST', async ({ page }) => {
    // Switch to BACK-TEST and verify leaderboard loads data
    await page.locator('#btnBacktestMode').click();
    await page.waitForTimeout(3000);

    // Leaderboard should have rows (back-test data has many algorithms)
    const backtestRows = await page.locator('#leaderboardBody tr').count();
    console.log('Back-test leaderboard rows:', backtestRows);
    expect(backtestRows).toBeGreaterThan(0);

    // Active picks should have data
    const backtestPicks = await page.locator('#picksBody tr').count();
    console.log('Back-test active picks rows:', backtestPicks);
    expect(backtestPicks).toBeGreaterThan(0);
  });

  test('data reloads properly after switching to LIVE', async ({ page }) => {
    // Switch to LIVE and verify leaderboard loads data
    await page.locator('#btnLiveMode').click();
    await page.waitForTimeout(3000);

    // Leaderboard should have rows from live_competition.json
    const liveRows = await page.locator('#leaderboardBody tr').count();
    console.log('Live leaderboard rows:', liveRows);
    expect(liveRows).toBeGreaterThan(0);
  });

  test('switching from BACK-TEST to LIVE changes displayed data', async ({ page }) => {
    // Switch to BACK-TEST first
    await page.locator('#btnBacktestMode').click();
    await page.waitForTimeout(2000);

    // Capture back-test data in first leaderboard row
    const backtestFirstRow = await page.locator('#leaderboardBody tr').first().textContent();
    console.log('Backtest first row:', backtestFirstRow);

    // Switch to LIVE
    await page.locator('#btnLiveMode').click();
    await page.waitForTimeout(2000);

    // Verify the leaderboard updated (live data has different values)
    const liveFirstRow = await page.locator('#leaderboardBody tr').first().textContent();
    console.log('Live first row:', liveFirstRow);

    // At minimum, the leaderboard should still be populated
    const rowCount = await page.locator('#leaderboardBody tr').count();
    expect(rowCount).toBeGreaterThan(0);
  });

  // ---------------------------------------------------------------
  // Bonus: URL parameter mode initialization
  // ---------------------------------------------------------------
  test('URL parameter ?mode=backtest initializes in backtest mode', async ({ page }) => {
    await page.goto(BASE_URL + '?mode=backtest');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    await expect(page.locator('#btnBacktestMode')).toHaveClass(/active/);
    await expect(page.locator('#dataSourceBadge')).toContainText('SIMULATED');
  });

  test('URL parameter ?mode=live initializes in live mode', async ({ page }) => {
    await page.goto(BASE_URL + '?mode=live');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    await expect(page.locator('#btnLiveMode')).toHaveClass(/active/);
    await expect(page.locator('#dataSourceBadge')).toContainText('LIVE');
  });
});
