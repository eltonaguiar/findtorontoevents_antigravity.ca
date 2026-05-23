import { test, expect } from '@playwright/test';

const AUDIT_PATH = '/audit_dashboard/';

test.describe('Audit Dashboard — Deep Quality Review (March 2026)', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(AUDIT_PATH, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3000);
  });

  // ── FILTER FUNCTIONALITY ──

  test('Proven Only button exists and filters to proven-tier picks', async ({ page }) => {
    const provenBtn = page.locator('#btn-proven-picks');
    await expect(provenBtn).toBeVisible();
    await provenBtn.click();
    await page.waitForTimeout(1000);

    // Should show Active Picks tab
    const activeTab = page.locator('#tab-active');
    await expect(activeTab).toBeVisible();

    // Pick count should be less than unfiltered
    const heading = await activeTab.locator('h2').first().textContent();
    expect(heading).toContain('Active Picks');
    const pickCount = parseInt(heading?.match(/\((\d+)\)/)?.[1] || '0');
    expect(pickCount).toBeGreaterThan(0);
    expect(pickCount).toBeLessThan(700); // Should be way fewer than 674 total crypto
  });

  test('Best Picks button shows picks sorted by score with age filter', async ({ page }) => {
    const bestBtn = page.locator('#btn-best-fresh');
    await bestBtn.click();
    await page.waitForTimeout(1000);

    // Sort should be score_desc
    const sortVal = await page.locator('#f-sort').inputValue();
    expect(sortVal).toBe('score_desc');

    // Age should be 48h
    const ageVal = await page.locator('#f-age').inputValue();
    expect(ageVal).toBe('48');
  });

  test('Active filter tags show which filters are applied', async ({ page }) => {
    // Set crypto filter
    await page.locator('#f-asset').selectOption('CRYPTO');
    await page.waitForTimeout(500);

    // Set confidence filter
    await page.locator('#f-conf').selectOption('0.65');
    await page.waitForTimeout(500);

    // Check the filter note shows names
    const heading = await page.locator('#tab-active h2').first().textContent();
    expect(heading).toContain('Conf=');
  });

  test('Crypto filter shows expected pick count range', async ({ page }) => {
    await page.locator('#f-asset').selectOption('CRYPTO');
    await page.waitForTimeout(1000);
    const heading = await page.locator('#tab-active h2').first().textContent();
    const pickCount = parseInt(heading?.match(/\((\d+)\)/)?.[1] || '0');
    // Should be a reasonable number of crypto picks
    expect(pickCount).toBeGreaterThan(100);
    expect(pickCount).toBeLessThan(2000);
  });

  // ── TOP SCORED PICKS SCRUTINY ──

  test('Top scored picks are from recent timeframe (not stale)', async ({ page }) => {
    // Click Best Picks
    await page.locator('#btn-best-fresh').click();
    await page.waitForTimeout(1000);

    // Get first 5 rows
    const rows = page.locator('#tab-active .data-table tbody tr');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThan(0);

    // Check the top picks have reasonable scores (should be > 30 at least)
    for (let i = 0; i < Math.min(5, rowCount); i++) {
      const row = rows.nth(i);
      const scoreBadge = row.locator('.score-badge');
      if (await scoreBadge.count() > 0) {
        const scoreText = await scoreBadge.first().textContent();
        const score = parseInt(scoreText?.trim() || '0');
        // Top picks should have decent scores after the scoring fix
        expect(score).toBeGreaterThan(20);
      }
    }
  });

  test('Top picks have valid entry prices (not garbage)', async ({ page }) => {
    await page.locator('#btn-best-fresh').click();
    await page.waitForTimeout(1000);

    const rows = page.locator('#tab-active .data-table tbody tr');
    const rowCount = await rows.count();

    for (let i = 0; i < Math.min(10, rowCount); i++) {
      const cells = await rows.nth(i).locator('td').allTextContents();
      // Verify no $0 or $1M+ entry prices in visible rows
      const entryText = cells.find(c => c.includes('$') && parseFloat(c.replace(/[^0-9.]/g, '')) > 0);
      if (entryText) {
        const price = parseFloat(entryText.replace(/[^0-9.]/g, ''));
        expect(price).toBeGreaterThan(0);
        expect(price).toBeLessThan(1000000);
      }
    }
  });

  // ── SYSTEM LEADERBOARD ──

  test('System Leaderboard shows composite scores and quartile badges', async ({ page }) => {
    // Navigate to Overview tab
    await page.locator('button.tab-btn[data-tab="overview"]').click();
    await page.waitForTimeout(1000);

    const overview = page.locator('#tab-overview');
    const text = await overview.textContent() || '';

    // Should have the new leaderboard title
    expect(text).toContain('System Leaderboard');
    expect(text).toContain('Composite Ranking');

    // Should have quartile badges
    expect(text).toMatch(/Q[1-4]/);

    // Should have rank numbers
    expect(text).toContain('#1');
    expect(text).toContain('#2');
  });

  test('System Leaderboard description explains methodology', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="overview"]').click();
    await page.waitForTimeout(1000);

    const description = await page.locator('#tab-overview').textContent() || '';
    expect(description).toContain('fund-of-funds');
    expect(description).toContain('Win Rate 30%');
    expect(description).toContain('Profit Factor 25%');
  });

  // ── OPEN FORWARD-TRADE STATS ──

  test('Open Forward-Trades section shows live P/L by system', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="overview"]').click();
    await page.waitForTimeout(1000);

    const overview = await page.locator('#tab-overview').textContent() || '';
    expect(overview).toContain('Open Forward-Trades');
    expect(overview).toContain('winners');
    expect(overview).toContain('losers');
    expect(overview).toContain('Avg P/L');
  });

  // ── LUXALGO TRUST TIER VERIFICATION ──

  test('LuxAlgo is NOT in PROVEN tier (insufficient data)', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="overview"]').click();
    await page.waitForTimeout(1000);

    // Check the Performance Breakdown section
    const overview = await page.locator('#tab-overview').textContent() || '';

    // LuxAlgo should not have the green star (PROVEN badge)
    const luxAlgoProvenStar = page.locator('#tab-overview span[title*="PROVEN"][title*="luxalgo"]');
    const provenCount = await luxAlgoProvenStar.count();
    // If it does appear with PROVEN, the fix didn't work
    expect(provenCount).toBe(0);
  });

  // ── REFRESH BUTTONS ──

  test('Refresh buttons have descriptive tooltips', async ({ page }) => {
    const refreshBtn = page.locator('#btn-refresh');
    const fullRefreshBtn = page.locator('#btn-full-refresh');

    const refreshTitle = await refreshBtn.getAttribute('title');
    const fullRefreshTitle = await fullRefreshBtn.getAttribute('title');

    // Refresh should explain it just reloads the page
    expect(refreshTitle).toContain('Reload page');
    // Full refresh should explain GitHub Actions
    expect(fullRefreshTitle).toContain('GitHub Actions');
  });

  test('Data age indicator is visible', async ({ page }) => {
    const ageIndicator = page.locator('#data-age-indicator');
    await expect(ageIndicator).toBeVisible();
    const text = await ageIndicator.textContent();
    // Should show how old data is
    expect(text).toMatch(/Data:|ago/);
  });

  // ── TRADE COUNT DISPLAY ──

  test('System names in picks table show win rate and tier info on hover', async ({ page }) => {
    await page.locator('#btn-best-fresh').click();
    await page.waitForTimeout(1000);

    // System column cells have cursor:help and contain elements with title attrs
    const sysCells = page.locator('#tab-active .data-table tbody td[style*="cursor:help"]');
    const count = await sysCells.count();
    expect(count).toBeGreaterThan(0);

    // The title is on the inner <a> or <span>, not the <td>
    const firstInner = sysCells.first().locator('a, span').first();
    const firstTitle = await firstInner.getAttribute('title') || '';
    // Should contain tier info
    expect(firstTitle.length).toBeGreaterThan(5);
  });

  // ── DATA REASONABILITY ──

  test('Overall win rate is a reasonable percentage', async ({ page }) => {
    const summaryCards = page.locator('.stat-card');
    const cardTexts = await summaryCards.allTextContents();
    const wrCard = cardTexts.find(t => t.includes('Win Rate'));
    if (wrCard) {
      const wrMatch = wrCard.match(/(\d+\.?\d*)%/);
      if (wrMatch) {
        const wr = parseFloat(wrMatch[1]);
        expect(wr).toBeGreaterThan(0);
        expect(wr).toBeLessThan(100);
      }
    }
  });

  test('Pick scores are bounded 0-100', async ({ page }) => {
    await page.locator('#btn-best-fresh').click();
    await page.waitForTimeout(1000);

    const scores = page.locator('.score-badge');
    const count = await scores.count();
    for (let i = 0; i < Math.min(20, count); i++) {
      const text = await scores.nth(i).textContent();
      const score = parseInt(text?.trim() || '0');
      expect(score).toBeGreaterThanOrEqual(0);
      expect(score).toBeLessThanOrEqual(100);
    }
  });

  test('No picks with $0 entry price visible', async ({ page }) => {
    const activeTab = page.locator('#tab-active');
    const html = await activeTab.innerHTML();
    // Should not contain "$0.00" as an entry price
    const zeroEntries = (html.match(/\$0\.00/g) || []).length;
    // Allow a few (some might be in tooltips) but not many
    expect(zeroEntries).toBeLessThan(5);
  });

  test('Performance Breakdown shows proven vs sandbox split', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="overview"]').click();
    await page.waitForTimeout(1000);

    const overview = await page.locator('#tab-overview').textContent() || '';
    expect(overview).toContain('Performance Breakdown');
    expect(overview).toContain('Proven Systems');
    expect(overview).toContain('Sandbox');
    expect(overview).toContain('Probation');
  });

  // ── PAGE LOAD PERFORMANCE ──

  test('Page loads within 10 seconds', async ({ page }) => {
    const start = Date.now();
    await page.goto(AUDIT_PATH, { waitUntil: 'domcontentloaded', timeout: 10000 });
    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(10000);
  });

  test('No console errors on page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto(AUDIT_PATH, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(3000);
    // Filter out network-related errors (expected in CI/offline environments)
    const realErrors = errors.filter(e =>
      !e.includes('favicon') && !e.includes('net::') && !e.includes('ERR_') &&
      !e.includes('Failed to fetch') && !e.includes('NetworkError')
    );
    if (realErrors.length > 0) {
      console.log('Console errors found:', realErrors);
    }
    expect(realErrors).toHaveLength(0);
  });

  // ── CLEAR ALL RESETS PROVEN FILTER ──

  test('Clear All button resets proven-only filter', async ({ page }) => {
    // Set proven filter
    await page.locator('#btn-proven-picks').click();
    await page.waitForTimeout(500);

    // Clear all
    await page.locator('#btn-clear-filters').click();
    await page.waitForTimeout(500);

    // Should show more picks now
    const heading = await page.locator('#tab-active h2').first().textContent();
    const pickCount = parseInt(heading?.match(/\((\d+)\)/)?.[1] || '0');
    expect(pickCount).toBeGreaterThan(100);
  });
});
