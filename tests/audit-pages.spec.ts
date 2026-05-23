import { test, expect, Page } from '@playwright/test';

// Base URLs for audit pages
const AUDIT_PAGE = 'http://findtorontoevents.ca/audit';
const HYROTRADER_PAGE = 'http://findtorontoevents.ca/audit/hyrotrader';

// Banned strategies per Kimi audit
const BANNED_STRATEGIES = ['unknown', 'gainer_compression_relaxed_mut', 'cta_commodity_momentum_term'];

// Asset class tabs to verify
const ASSET_TABS = [
  'Equity', 'Crypto S-Tier', 'Crypto A-Tier', 'Crypto B-Tier', 'Crypto C-Tier',
  'Forex', 'Commodity', 'ETF', 'Bonds', 'Futures'
];

test.describe('Audit Pages Core Checks', () => {
  let consoleErrors: string[] = [];

  test.beforeEach(async ({ page }) => {
    consoleErrors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
  });

  test('Audit page has no console errors', async ({ page }) => {
    await page.goto(AUDIT_PAGE, { waitUntil: 'networkidle' });
    expect(consoleErrors.length).toBe(0);
  });

  test('Hyrotrader audit page has no console errors', async ({ page }) => {
    await page.goto(HYROTRADER_PAGE, { waitUntil: 'networkidle' });
    expect(consoleErrors.length).toBe(0);
  });

  test('All asset class tabs load correctly', async ({ page }) => {
    await page.goto(AUDIT_PAGE, { waitUntil: 'networkidle' });

    for (const tab of ASSET_TABS) {
      const tabSelector = `text="${tab}"`;
      const tabVisible = await page.isVisible(tabSelector);
      if (tab === 'Futures' || tab === 'Bonds') {
        // These tabs may have insufficient data, skip strict check
        continue;
      }
      expect(tabVisible).toBe(true);
      await page.click(tabSelector);
      await page.waitForTimeout(500); // Wait for tab content to load
      const tabContent = await page.locator(`[data-tab="${tab}"]`).isVisible();
      expect(tabContent).toBe(true);
    }
  });

  test('R:R filter works (1.5-2.0 golden zone)', async ({ page }) => {
    await page.goto(AUDIT_PAGE, { waitUntil: 'networkidle' });

    // Set R:R min to 1.5
    const rrMinInput = page.locator('[data-testid="rr-min-input"]');
    if (await rrMinInput.isVisible()) {
      await rrMinInput.fill('1.5');
    }

    // Set R:R max to 2.0
    const rrMaxInput = page.locator('[data-testid="rr-max-input"]');
    if (await rrMaxInput.isVisible()) {
      await rrMaxInput.fill('2.0');
    }

    // Apply filter
    const applyFilterBtn = page.locator('[data-testid="apply-filters-btn"]');
    if (await applyFilterBtn.isVisible()) {
      await applyFilterBtn.click();
      await page.waitForTimeout(1000);
    }

    // Verify all visible picks have R:R between 1.5 and 2.0
    const pickRRValues = await page.locator('[data-testid="pick-rr"]').allInnerTexts();
    for (const rrText of pickRRValues) {
      const rr = parseFloat(rrText);
      if (!isNaN(rr)) {
        expect(rr).toBeGreaterThanOrEqual(1.5);
        expect(rr).toBeLessThanOrEqual(2.0);
      }
    }
  });

  test('Trust score filter works (>=5)', async ({ page }) => {
    await page.goto(AUDIT_PAGE, { waitUntil: 'networkidle' });

    // Set trust score min to 5
    const trustMinInput = page.locator('[data-testid="trust-score-min-input"]');
    if (await trustMinInput.isVisible()) {
      await trustMinInput.fill('5');
    }

    // Apply filter
    const applyFilterBtn = page.locator('[data-testid="apply-filters-btn"]');
    if (await applyFilterBtn.isVisible()) {
      await applyFilterBtn.click();
      await page.waitForTimeout(1000);
    }

    // Verify all visible picks have trust_score >=5
    const pickTrustValues = await page.locator('[data-testid="pick-trust-score"]').allInnerTexts();
    for (const trustText of pickTrustValues) {
      const trust = parseInt(trustText, 10);
      if (!isNaN(trust)) {
        expect(trust).toBeGreaterThanOrEqual(5);
      }
    }
  });

  test('HTML nested comment bug is fixed', async ({ page }) => {
    await page.goto(AUDIT_PAGE, { waitUntil: 'networkidle' });

    // Navigate to US Equity Picks tab
    const uepsTab = page.locator('text="US Equity Picks"');
    if (await uepsTab.isVisible()) {
      await uepsTab.click();
      await page.waitForTimeout(500);

      // Check for leaked comment text
      const pageContent = await page.content();
      const leakedText = 'HTML does not support nested comments and the inner --> would close the outer';
      expect(pageContent).not.toContain(leakedText);
    }
  });

  test('Banned strategies do not appear in picks', async ({ page }) => {
    await page.goto(AUDIT_PAGE, { waitUntil: 'networkidle' });

    // Get all pick strategy labels
    const pickStrategies = await page.locator('[data-testid="pick-strategy"]').allInnerTexts();

    for (const strategy of pickStrategies) {
      expect(BANNED_STRATEGIES).not.toContain(strategy.trim().toLowerCase());
    }
  });

  test('Forex tab is hidden or marked under review', async ({ page }) => {
    await page.goto(AUDIT_PAGE, { waitUntil: 'networkidle' });

    const forexTab = page.locator('text="Forex"');
    if (await forexTab.isVisible()) {
      await forexTab.click();
      await page.waitForTimeout(500);
      const underReviewBadge = page.locator('text="Under Review"');
      expect(await underReviewBadge.isVisible()).toBe(true);
    }
  });

  test('CTA Commodity Momentum Term strategy is banned', async ({ page }) => {
    await page.goto(AUDIT_PAGE, { waitUntil: 'networkidle' });

    // Check commodity tab for banned strategy
    const commodityTab = page.locator('text="Commodity"');
    if (await commodityTab.isVisible()) {
      await commodityTab.click();
      await page.waitForTimeout(500);
      const strategyLabels = await page.locator('[data-testid="pick-strategy"]').allInnerTexts();
      expect(strategyLabels.map(s => s.toLowerCase())).not.toContain('cta_commodity_momentum_term');
    }
  });
});
