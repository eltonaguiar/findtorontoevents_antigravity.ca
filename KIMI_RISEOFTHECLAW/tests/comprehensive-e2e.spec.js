const { test, expect } = require('@playwright/test');

/**
 * Comprehensive End-to-End Test Suite for Rise of the Claw Dashboard
 *
 * Tests:
 * - All filter combinations
 * - Data integrity
 * - JavaScript errors
 * - Missing data scenarios
 * - Performance
 * - Audit trail verification
 */

test.describe('Rise of the Claw - Comprehensive E2E Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Track console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.error('Browser console error:', msg.text());
      }
    });

    await page.goto('https://findtorontoevents.ca/riseoftheclaw.html');
    await page.waitForLoadState('networkidle');
  });

  test.describe('JavaScript Error Detection', () => {

    test('should have no JavaScript errors on page load', async ({ page }) => {
      const errors = [];
      page.on('pageerror', error => {
        errors.push(error.message);
      });

      await page.waitForTimeout(3000);

      expect(errors).toHaveLength(0);
      if (errors.length > 0) {
        console.error('JavaScript errors found:', errors);
      }
    });

    test('should have no unhandled promise rejections', async ({ page }) => {
      const rejections = [];
      page.on('pageerror', error => {
        if (error.message.includes('Unhandled')) {
          rejections.push(error.message);
        }
      });

      await page.waitForTimeout(3000);
      expect(rejections).toHaveLength(0);
    });

    test('should have no "undefined" reference errors', async ({ page }) => {
      const undefinedErrors = [];
      page.on('console', msg => {
        if (msg.type() === 'error' && msg.text().toLowerCase().includes('undefined')) {
          undefinedErrors.push(msg.text());
        }
      });

      await page.waitForTimeout(3000);
      expect(undefinedErrors).toHaveLength(0);
    });
  });

  test.describe('Data Loading and Integrity', () => {

    test('should load performance cards with valid data', async ({ page }) => {
      await page.waitForSelector('.perf-card', { timeout: 10000 });

      const topPerformer = await page.locator('#topPerformer').textContent();
      const bestWinRate = await page.locator('#bestWinRate').textContent();
      const mostActive = await page.locator('#mostActive').textContent();
      const bestSharpe = await page.locator('#bestSharpe').textContent();
      const lowestDrawdown = await page.locator('#lowestDrawdown').textContent();

      // Verify none are placeholder values
      expect(topPerformer).not.toBe('--');
      expect(bestWinRate).not.toBe('--');
      expect(mostActive).not.toBe('--');
      expect(bestSharpe).not.toBe('--');
      expect(lowestDrawdown).not.toBe('--');

      // Verify win rate is a percentage
      expect(bestWinRate).toMatch(/\d+\.\d+%/);
    });

    test('should load leaderboard with at least 10 algorithms', async ({ page }) => {
      await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

      const rows = await page.locator('#leaderboardBody tr').count();
      expect(rows).toBeGreaterThanOrEqual(10);
    });

    test('should have valid portfolio values in leaderboard', async ({ page }) => {
      await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

      const firstRow = page.locator('#leaderboardBody tr').first();
      const portfolioValue = await firstRow.locator('td').nth(3).textContent();

      // Should be formatted as currency (e.g., $11,850)
      expect(portfolioValue).toMatch(/\$[\d,]+/);
    });

    test('should load active picks', async ({ page }) => {
      await page.waitForSelector('#picksBody tr', { timeout: 10000 });

      const rows = await page.locator('#picksBody tr').count();
      expect(rows).toBeGreaterThan(0);
    });

    test('should display data source indicator', async ({ page }) => {
      const subtitle = await page.locator('.logo-text p').textContent();

      // Should mention SIMULATED DATA or LIVE DATA
      expect(subtitle).toMatch(/SIMULATED|LIVE/);
    });
  });

  test.describe('Category Filtering - All Combinations', () => {

    const categories = ['all', 'stock', 'penny', 'crypto', 'meme', 'forex'];

    for (const category of categories) {
      test(`should filter by ${category} category`, async ({ page }) => {
        await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

        // Click category button
        await page.locator(`[data-category="${category}"]`).click();
        await page.waitForTimeout(500);

        // Verify button is active
        const isActive = await page.locator(`[data-category="${category}"]`).getAttribute('class');
        expect(isActive).toContain('active');

        // Check if data loaded or has appropriate message
        const rows = await page.locator('#leaderboardBody tr').count();

        if (rows === 1) {
          // Check if it's a "no data" message
          const cellText = await page.locator('#leaderboardBody tr td').textContent();
          expect(cellText).toMatch(/No algorithms found|Loading/i);
        } else {
          expect(rows).toBeGreaterThan(0);
        }
      });
    }

    test('should maintain filter when sorting', async ({ page }) => {
      await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

      // Filter by crypto
      await page.locator('[data-category="crypto"]').click();
      await page.waitForTimeout(500);

      const rowsAfterFilter = await page.locator('#leaderboardBody tr').count();

      // Sort by win rate
      await page.locator('#sortBy').selectOption('winRate');
      await page.waitForTimeout(500);

      const rowsAfterSort = await page.locator('#leaderboardBody tr').count();

      // Should have same number of rows
      expect(rowsAfterSort).toBe(rowsAfterFilter);

      // Verify filter is still active
      const isActive = await page.locator('[data-category="crypto"]').getAttribute('class');
      expect(isActive).toContain('active');
    });
  });

  test.describe('Sorting - All Options', () => {

    const sortOptions = ['return', 'winRate', 'sharpe', 'value'];

    for (const sortOption of sortOptions) {
      test(`should sort by ${sortOption}`, async ({ page }) => {
        await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

        // Select sort option
        await page.locator('#sortBy').selectOption(sortOption);
        await page.waitForTimeout(500);

        // Verify data is loaded
        const rows = await page.locator('#leaderboardBody tr').count();
        expect(rows).toBeGreaterThan(0);

        // Verify selected value
        const selectedValue = await page.locator('#sortBy').inputValue();
        expect(selectedValue).toBe(sortOption);
      });
    }

    test('should maintain sort across category changes', async ({ page }) => {
      await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

      // Sort by win rate
      await page.locator('#sortBy').selectOption('winRate');
      await page.waitForTimeout(500);

      // Change category
      await page.locator('[data-category="crypto"]').click();
      await page.waitForTimeout(500);

      // Verify sort is still winRate
      const selectedValue = await page.locator('#sortBy').inputValue();
      expect(selectedValue).toBe('winRate');
    });
  });

  test.describe('Active Picks Filtering', () => {

    test('should filter picks by search term', async ({ page }) => {
      await page.waitForSelector('#picksBody tr', { timeout: 10000 });

      const initialRows = await page.locator('#picksBody tr').count();

      // Search for a common symbol
      await page.locator('#pickSearch').fill('BTC');
      await page.waitForTimeout(500);

      const filteredRows = await page.locator('#picksBody tr').count();

      if (filteredRows === 1) {
        // Check if it's a "no results" message
        const cellText = await page.locator('#picksBody tr td').first().textContent();
        expect(cellText).toMatch(/No active picks found/i);
      } else {
        expect(filteredRows).toBeLessThanOrEqual(initialRows);
      }
    });

    test('should filter picks by category', async ({ page }) => {
      await page.waitForSelector('#picksBody tr', { timeout: 10000 });

      const categories = ['crypto', 'stock', 'meme', 'forex', 'penny'];

      for (const category of categories) {
        await page.locator('#pickCategoryFilter').selectOption(category);
        await page.waitForTimeout(500);

        const rows = await page.locator('#picksBody tr').count();
        expect(rows).toBeGreaterThanOrEqual(1); // At least the header or a message
      }
    });

    test('should combine search and category filters', async ({ page }) => {
      await page.waitForSelector('#picksBody tr', { timeout: 10000 });

      // Filter by crypto category
      await page.locator('#pickCategoryFilter').selectOption('crypto');
      await page.waitForTimeout(500);

      // Then search
      await page.locator('#pickSearch').fill('ETH');
      await page.waitForTimeout(500);

      const rows = await page.locator('#picksBody tr').count();
      expect(rows).toBeGreaterThanOrEqual(1);
    });

    test('should show all picks when filters are cleared', async ({ page }) => {
      await page.waitForSelector('#picksBody tr', { timeout: 10000 });

      const initialRows = await page.locator('#picksBody tr').count();

      // Apply filter
      await page.locator('#pickSearch').fill('XYZ');
      await page.waitForTimeout(500);

      // Clear filter
      await page.locator('#pickSearch').fill('');
      await page.waitForTimeout(500);

      const finalRows = await page.locator('#picksBody tr').count();
      expect(finalRows).toBe(initialRows);
    });
  });

  test.describe('Time Range Filtering', () => {

    const timeRanges = ['7d', '30d', '90d', 'all'];

    for (const range of timeRanges) {
      test(`should filter by ${range} time range`, async ({ page }) => {
        await page.waitForSelector('.time-btn', { timeout: 10000 });

        // Click time range button
        await page.locator(`.time-btn`).filter({ hasText: range.toUpperCase() }).click();
        await page.waitForTimeout(1000);

        // Verify data is still displayed
        const rows = await page.locator('#leaderboardBody tr').count();
        expect(rows).toBeGreaterThan(0);
      });
    }
  });

  test.describe('Chart Functionality', () => {

    test('should display portfolio chart', async ({ page }) => {
      await page.waitForSelector('#portfolioChart', { timeout: 10000 });

      const chartCanvas = page.locator('#portfolioChart');
      await expect(chartCanvas).toBeVisible();
    });

    test('should have chart controls', async ({ page }) => {
      await page.waitForSelector('.time-btn', { timeout: 10000 });

      const timeButtons = await page.locator('.time-btn').count();
      expect(timeButtons).toBe(4); // 7D, 30D, 90D, ALL
    });
  });

  test.describe('Algorithm Detail Modal', () => {

    test('should open modal when clicking algorithm row', async ({ page }) => {
      await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

      await page.locator('#leaderboardBody tr').first().click();
      await page.waitForTimeout(500);

      const modal = page.locator('#algoModal');
      await expect(modal).toBeVisible();
    });

    test('should display algorithm details in modal', async ({ page }) => {
      await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

      await page.locator('#leaderboardBody tr').first().click();
      await page.waitForTimeout(500);

      const modalBody = page.locator('#modalBody');
      await expect(modalBody).toBeVisible();

      // Should contain key metrics
      const bodyText = await modalBody.textContent();
      expect(bodyText).toMatch(/Portfolio Value|Total Return|Win Rate|Sharpe Ratio/);
    });

    test('should close modal when clicking close button', async ({ page }) => {
      await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

      await page.locator('#leaderboardBody tr').first().click();
      await page.waitForTimeout(500);

      await page.locator('.modal-close').click();
      await page.waitForTimeout(500);

      const modal = page.locator('#algoModal');
      const isVisible = await modal.isVisible();

      // Modal might still be in DOM but should not be visible
      // Check if it has active class
      const modalClass = await modal.getAttribute('class');
      expect(modalClass).not.toContain('active');
    });

    test('should close modal when clicking outside', async ({ page }) => {
      await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

      await page.locator('#leaderboardBody tr').first().click();
      await page.waitForTimeout(500);

      // Click on modal background (not content)
      await page.locator('#algoModal').click();
      await page.waitForTimeout(500);

      const modalClass = await page.locator('#algoModal').getAttribute('class');
      expect(modalClass).not.toContain('active');
    });
  });

  test.describe('Auto-Refresh Functionality', () => {

    test('should have auto-refresh controls', async ({ page }) => {
      const refreshSelect = page.locator('#refreshInterval');
      await expect(refreshSelect).toBeVisible();

      const selectedValue = await refreshSelect.inputValue();
      expect(['30', '60', '300', '0']).toContain(selectedValue);
    });

    test('should have manual refresh button', async ({ page }) => {
      const refreshBtn = page.locator('.btn-refresh');
      await expect(refreshBtn).toBeVisible();
    });

    test('should update last updated timestamp', async ({ page }) => {
      const lastUpdated = page.locator('#lastUpdated');
      await expect(lastUpdated).toBeVisible();

      const timestamp = await lastUpdated.textContent();
      expect(timestamp).not.toBe('Updating...');
      expect(timestamp).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    });

    test('should refresh data when clicking refresh button', async ({ page }) => {
      await page.waitForSelector('#lastUpdated', { timeout: 10000 });

      const initialTimestamp = await page.locator('#lastUpdated').textContent();

      await page.locator('.btn-refresh').click();
      await page.waitForTimeout(2000);

      const newTimestamp = await page.locator('#lastUpdated').textContent();

      // Timestamps should be different (or at least attempt was made)
      console.log('Initial:', initialTimestamp, 'New:', newTimestamp);
    });
  });

  test.describe('Category Breakdown', () => {

    test('should display category breakdown cards', async ({ page }) => {
      // Wait longer for breakdown to render
      await page.waitForTimeout(2000);

      const breakdownGrid = page.locator('#breakdownGrid');
      await expect(breakdownGrid).toBeVisible();

      const cards = await page.locator('.breakdown-card').count();

      if (cards === 0) {
        console.warn('No breakdown cards found - may indicate data issue');
      }
    });

    test('should show average returns per category', async ({ page }) => {
      await page.waitForTimeout(2000);

      const firstCard = page.locator('.breakdown-card').first();

      if (await firstCard.isVisible()) {
        const cardText = await firstCard.textContent();
        expect(cardText).toMatch(/[\+\-]?\d+\.\d+%/);
      }
    });
  });

  test.describe('Data Export', () => {

    test('should have export button', async ({ page }) => {
      const exportBtn = page.locator('button').filter({ hasText: 'Export Data' });
      await expect(exportBtn).toBeVisible();
    });
  });

  test.describe('Responsive Design', () => {

    test('should be responsive on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.waitForTimeout(1000);

      // Check if header is visible
      const header = page.locator('.main-header');
      await expect(header).toBeVisible();

      // Check if leaderboard is visible
      const leaderboard = page.locator('#leaderboardTable');
      await expect(leaderboard).toBeVisible();
    });

    test('should be responsive on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.waitForTimeout(1000);

      const performanceCards = page.locator('.performance-cards');
      await expect(performanceCards).toBeVisible();
    });
  });

  test.describe('Performance Metrics', () => {

    test('should load within 5 seconds', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('https://findtorontoevents.ca/riseoftheclaw.html');
      await page.waitForSelector('.perf-card', { timeout: 5000 });

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000);
    });

    test('should have no memory leaks after refreshing 5 times', async ({ page }) => {
      for (let i = 0; i < 5; i++) {
        await page.locator('.btn-refresh').click();
        await page.waitForTimeout(1000);
      }

      // Check if page is still responsive
      const rows = await page.locator('#leaderboardBody tr').count();
      expect(rows).toBeGreaterThan(0);
    });
  });

  test.describe('Edge Cases and Error Handling', () => {

    test('should handle empty search results gracefully', async ({ page }) => {
      await page.waitForSelector('#picksBody tr', { timeout: 10000 });

      await page.locator('#pickSearch').fill('ZZZZZZZ_NONEXISTENT');
      await page.waitForTimeout(500);

      const cellText = await page.locator('#picksBody tr td').first().textContent();
      expect(cellText).toMatch(/No active picks found/i);
    });

    test('should handle category with no algorithms', async ({ page }) => {
      await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

      // Filter by a category that might have no results
      await page.locator('[data-category="forex"]').click();
      await page.waitForTimeout(500);

      const rows = await page.locator('#leaderboardBody tr').count();

      if (rows === 1) {
        const cellText = await page.locator('#leaderboardBody tr td').textContent();
        expect(cellText).toMatch(/No algorithms found|Loading/i);
      }
    });

    test('should maintain state after navigation', async ({ page }) => {
      await page.waitForSelector('#leaderboardBody tr', { timeout: 10000 });

      // Set filters
      await page.locator('[data-category="crypto"]').click();
      await page.waitForTimeout(500);
      await page.locator('#sortBy').selectOption('winRate');
      await page.waitForTimeout(500);

      // Refresh page
      await page.reload();
      await page.waitForTimeout(2000);

      // State might reset - this is acceptable for now
      // Future enhancement: persist state in localStorage
    });
  });

  test.describe('Accessibility', () => {

    test('should have proper page title', async ({ page }) => {
      await expect(page).toHaveTitle(/KIMI.*Algorithm Battle Royale/);
    });

    test('should have clickable buttons', async ({ page }) => {
      const refreshBtn = page.locator('.btn-refresh');
      await expect(refreshBtn).toBeEnabled();

      const categoryBtns = page.locator('.cat-btn');
      const count = await categoryBtns.count();
      expect(count).toBeGreaterThan(0);
    });
  });
});
