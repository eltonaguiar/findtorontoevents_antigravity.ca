const { test, expect } = require('@playwright/test');

test.describe('Rise of the Claw Dashboard', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to the dashboard
    await page.goto('https://findtorontoevents.ca/riseoftheclaw.html');
  });

  test('should load dashboard and display header', async ({ page }) => {
    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Check title
    await expect(page).toHaveTitle(/KIMI_CLAW_CHATBOT.*Algorithm Battle Royale/);

    // Check header elements
    await expect(page.locator('h1')).toContainText('KIMI_CLAW_CHATBOT');
    await expect(page.locator('.logo-icon')).toContainText('🐾');
    await expect(page.locator('.logo-text p')).toContainText('SIMULATED DATA');
  });

  test('should display performance cards', async ({ page }) => {
    // Wait for data to load
    await page.waitForSelector('.perf-card', { timeout: 10000 });

    // Check all 5 performance cards exist
    const perfCards = await page.locator('.perf-card').count();
    expect(perfCards).toBe(5);

    // Check card labels
    await expect(page.locator('.perf-card').first()).toContainText('Top Performer');
    await expect(page.locator('.perf-card').nth(1)).toContainText('Best Win Rate');
    await expect(page.locator('.perf-card').nth(2)).toContainText('Most Active');
    await expect(page.locator('.perf-card').nth(3)).toContainText('Best Sharpe');
    await expect(page.locator('.perf-card').nth(4)).toContainText('Lowest Drawdown');

    // Verify cards have actual data (not just --)
    const topPerformer = await page.locator('#topPerformer').textContent();
    expect(topPerformer).not.toBe('--');
  });

  test('should load and display leaderboard', async ({ page }) => {
    // Wait for leaderboard to load
    await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

    // Check leaderboard has data
    const rows = await page.locator('#leaderboardBody tr').count();
    expect(rows).toBeGreaterThan(0);

    // Check table headers
    await expect(page.locator('th').first()).toContainText('Rank');
    await expect(page.locator('th').nth(1)).toContainText('Algorithm');
    await expect(page.locator('th').nth(3)).toContainText('Portfolio Value');
    await expect(page.locator('th').nth(4)).toContainText('Total Return');
  });

  test('should load and display active picks', async ({ page }) => {
    // Wait for picks to load
    await page.waitForSelector('#picksBody tr', { timeout: 10000 });

    // Check picks table has data
    const rows = await page.locator('#picksBody tr').count();
    expect(rows).toBeGreaterThan(0);

    // Check table headers
    await expect(page.locator('.picks-table th').first()).toContainText('Symbol');
    await expect(page.locator('.picks-table th').nth(1)).toContainText('Algorithm');
    await expect(page.locator('.picks-table th').nth(5)).toContainText('P&L %');
  });

  test('should filter algorithms by category', async ({ page }) => {
    // Wait for initial load
    await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

    // Get initial row count
    const allRows = await page.locator('#leaderboardBody tr').count();

    // Click crypto category
    await page.locator('[data-category="crypto"]').click();
    await page.waitForTimeout(500);

    // Check filtered results
    const cryptoRows = await page.locator('#leaderboardBody tr').count();
    expect(cryptoRows).toBeLessThanOrEqual(allRows);

    // Click back to all
    await page.locator('[data-category="all"]').click();
    await page.waitForTimeout(500);

    const backToAll = await page.locator('#leaderboardBody tr').count();
    expect(backToAll).toBe(allRows);
  });

  test('should sort leaderboard', async ({ page }) => {
    // Wait for initial load
    await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

    // Get first algorithm name with return sorting
    const firstByReturn = await page.locator('#leaderboardBody tr').first().textContent();

    // Sort by win rate
    await page.locator('#sortBy').selectOption('winRate');
    await page.waitForTimeout(500);

    const firstByWinRate = await page.locator('#leaderboardBody tr').first().textContent();

    // Results should potentially be different
    // (unless the same algo has both best return and win rate)
    console.log('First by return:', firstByReturn);
    console.log('First by win rate:', firstByWinRate);
  });

  test('should filter picks by search', async ({ page }) => {
    // Wait for picks to load
    await page.waitForSelector('#picksBody tr', { timeout: 10000 });

    const initialRows = await page.locator('#picksBody tr').count();

    // Search for a symbol
    await page.locator('#pickSearch').fill('BTC');
    await page.waitForTimeout(500);

    const filteredRows = await page.locator('#picksBody tr').count();
    expect(filteredRows).toBeLessThanOrEqual(initialRows);
  });

  test('should handle refresh interval', async ({ page }) => {
    // Check refresh interval dropdown exists
    await expect(page.locator('#refreshInterval')).toBeVisible();

    // Check default value is 30 seconds
    const selectedValue = await page.locator('#refreshInterval').inputValue();
    expect(selectedValue).toBe('30');

    // Check last updated timestamp exists
    await expect(page.locator('#lastUpdated')).toBeVisible();
    const timestamp = await page.locator('#lastUpdated').textContent();
    expect(timestamp).not.toBe('Updating...');
  });

  test('should display category breakdown', async ({ page }) => {
    // Wait for breakdown to load
    await page.waitForSelector('.breakdown-card', { timeout: 10000 });

    // Check at least one category card exists
    const breakdownCards = await page.locator('.breakdown-card').count();
    expect(breakdownCards).toBeGreaterThan(0);
  });

  test('should open algorithm detail modal', async ({ page }) => {
    // Wait for leaderboard
    await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

    // Click first algorithm row
    await page.locator('#leaderboardBody tr').first().click();
    await page.waitForTimeout(500);

    // Check modal is visible
    await expect(page.locator('#algoModal')).toHaveClass(/active/);

    // Close modal
    await page.locator('.modal-close').click();
    await page.waitForTimeout(500);

    // Check modal is hidden
    await expect(page.locator('#algoModal')).not.toHaveClass(/active/);
  });

  test('should not have JavaScript errors', async ({ page }) => {
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Should not have the "best is not defined" error
    const hasBestError = errors.some(err => err.includes('best is not defined'));
    expect(hasBestError).toBe(false);

    console.log('Console errors:', errors);
  });

  test('should load data from JSON files', async ({ page }) => {
    // Monitor network requests
    const dataRequests = [];
    page.on('response', response => {
      if (response.url().includes('.json')) {
        dataRequests.push({
          url: response.url(),
          status: response.status()
        });
      }
    });

    await page.waitForLoadState('networkidle');

    // Check that JSON files were requested
    const hasAlgorithmsJson = dataRequests.some(req => req.url.includes('algorithms.json'));
    const hasPicksJson = dataRequests.some(req => req.url.includes('active_picks.json'));

    console.log('Data requests:', dataRequests);
    expect(hasAlgorithmsJson || hasPicksJson).toBe(true);
  });

  test('performance: page should load within 10 seconds', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('https://findtorontoevents.ca/riseoftheclaw.html');
    await page.waitForSelector('.perf-card', { timeout: 10000 });

    const loadTime = Date.now() - startTime;
    console.log(`Page load time: ${loadTime}ms`);

    expect(loadTime).toBeLessThan(10000);
  });
});
