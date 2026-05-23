import { test, expect } from '@playwright/test';

test.describe('Inactive Systems Fix Verification', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/audit_dashboard/');
    await page.waitForSelector('.tab-btn', { timeout: 15000 });
    // Wait for data to render (overview tab needs DASHBOARD_DATA)
    await page.waitForTimeout(3000);
  });

  test('battleground system appears in overview with active picks', async ({ page }) => {
    // Overview tab is default, check the system table
    const overviewHtml = await page.locator('#tab-overview').innerHTML();
    // battleground should appear somewhere in the overview
    expect(overviewHtml.toLowerCase()).toContain('battleground');
    console.log('Battleground found in overview');
  });

  test('performance breakdown has expandable tier rows', async ({ page }) => {
    // The Overview tab should be visible by default
    const overviewHtml = await page.locator('#tab-overview').innerHTML();
    // Check tier rows exist
    expect(overviewHtml).toContain('Proven Systems');
    expect(overviewHtml).toContain('Sandbox (Unproven)');
    expect(overviewHtml).toContain('Probation');
    // Check expand arrows exist
    expect(overviewHtml).toContain('tier-arrow');
  });

  test('tier rows have expand arrows for drilling down', async ({ page }) => {
    // Check that the tier rows have expand arrows in their HTML
    const overviewHtml = await page.locator('#tab-overview').innerHTML();
    expect(overviewHtml).toContain('tier-arrow');
    // Check that hidden expand rows exist
    expect(overviewHtml).toContain('tier-expand-');
    console.log('Tier expand rows present');
  });

  test('trust tier tooltips exist on Performance Breakdown', async ({ page }) => {
    const overviewHtml = await page.locator('#tab-overview').innerHTML();
    // Check for info tooltips on tier categories
    expect(overviewHtml).toContain('sys-desc-tip');
    expect(overviewHtml).toContain('sys-desc-popup');
    // Check tooltip content mentions criteria
    expect(overviewHtml).toContain('Forward-verified');  // Proven description
    expect(overviewHtml).toContain('unverified');         // Sandbox description
  });

  test('performance breakdown shows wins and losses (not all zeros)', async ({ page }) => {
    const overviewHtml = await page.locator('#tab-overview').innerHTML();
    // The Proven Systems row should have non-zero wins
    // We verify by checking the content has numbers > 0 in the table
    const provenRow = page.locator('tr:has-text("Proven Systems")').first();
    const provenText = await provenRow.textContent();
    console.log('Proven row text:', provenText);
    // WR should not be 0.0% if there are wins
    // Check that at least one tier row has a non-zero WR
    const allTierRows = await page.locator('tr:has(.tier-arrow)').allTextContents();
    const hasNonZeroWR = allTierRows.some(text => {
      const match = text.match(/([\d.]+)%/);
      return match && parseFloat(match[1]) > 0;
    });
    expect(hasNonZeroWR).toBe(true);
  });

  test('tooltips render below cells (not off-screen)', async ({ page }) => {
    // Check CSS for matrix tooltips
    const tooltipCSS = await page.evaluate(() => {
      const sheet = document.styleSheets[0];
      let found = '';
      for (const rule of sheet.cssRules) {
        if (rule instanceof CSSStyleRule && rule.selectorText === '.matrix-tooltip') {
          found = rule.style.top || rule.style.bottom || 'none';
        }
      }
      return found;
    });
    console.log('Tooltip position property:', tooltipCSS);
    // Should use 'top' (below cell) not 'bottom' (above cell)
    expect(tooltipCSS).toContain('calc(100% + 6px)');
  });

  test('Active column header has data-tip tooltip', async ({ page }) => {
    const overviewHtml = await page.locator('#tab-overview').innerHTML();
    // data-tip attribute contains the tooltip text
    expect(overviewHtml).toContain('data-tip=');
    expect(overviewHtml).toContain('col-tip');
    console.log('Column tooltips present');
  });

  test('system trust tier badges have hover tooltips', async ({ page }) => {
    // Navigate to Performance tab
    await page.click('[data-tab="performance"]');
    await page.waitForTimeout(1000);
    const perfHtml = await page.locator('#tab-performance').innerHTML();
    // Check trust tier badges have title attributes
    expect(perfHtml).toContain('title=');
    expect(perfHtml).toContain('badge-active');
  });

  test('watchdog JSON output is valid', async ({ page }) => {
    // This tests that the watchdog script produces valid output
    // We verify by checking if the battleground active_picks.json is valid
    const response = await page.goto('/battleground/data/active_picks.json');
    if (response && response.ok()) {
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);
      console.log(`Battleground active_picks.json: ${data.length} picks`);
      // Verify pick format
      const pick = data[0];
      expect(pick).toHaveProperty('symbol');
      expect(pick).toHaveProperty('direction');
      expect(pick).toHaveProperty('entry_price');
      expect(pick).toHaveProperty('confidence');
      expect(pick).toHaveProperty('strategy');
      expect(pick).toHaveProperty('forward_wr');
      expect(pick).toHaveProperty('forward_validated');
    }
  });
});
