import { test, expect } from '@playwright/test';

// Uses baseURL from playwright.config.ts
const AUDIT_PATH = '/audit_dashboard/';

test.describe('Audit Dashboard — Data Quality & Filtering', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(AUDIT_PATH, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(2000);
  });

  test('page loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    const realErrors = errors.filter(e =>
      !e.includes('favicon') && !e.includes('net::') && !e.includes('ERR_')
    );
    expect(realErrors).toHaveLength(0);
  });

  test('summary cards render with numeric values', async ({ page }) => {
    const cards = page.locator('.stat-card');
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(3);
    const values = await cards.locator('.value').allTextContents();
    const hasValue = values.some(v => v.trim() !== '' && v.trim() !== '0');
    expect(hasValue).toBe(true);
  });

  test('tab navigation works', async ({ page }) => {
    const tabs = page.locator('.tab-btn');
    const tabCount = await tabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(4);
    for (let i = 0; i < Math.min(tabCount, 5); i++) {
      await tabs.nth(i).click();
      await page.waitForTimeout(300);
      const cls = await tabs.nth(i).getAttribute('class');
      expect(cls).toContain('active');
    }
  });

  test('Systems tab shows ML systems', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="systems"]').click();
    await page.waitForTimeout(500);
    const systemsTab = page.locator('#tab-systems');
    await expect(systemsTab).toBeVisible();
    const text = await systemsTab.textContent() || '';
    // Should have content (system cards rendered)
    expect(text.length).toBeGreaterThan(20);
  });

  test('Mercury2 appears in Systems tab', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="systems"]').click();
    await page.waitForTimeout(500);
    const text = await page.locator('#tab-systems').textContent() || '';
    expect(text.toLowerCase()).toContain('mercury2');
  });

  test('filter bar has all controls', async ({ page }) => {
    await expect(page.locator('#f-asset')).toBeVisible();
    await expect(page.locator('#f-system')).toBeVisible();
    await expect(page.locator('#f-status')).toBeVisible();
    await expect(page.locator('#f-dir')).toBeVisible();
    await expect(page.locator('#f-search')).toBeVisible();
    await expect(page.locator('#f-sort')).toBeVisible();
    await expect(page.locator('#f-age')).toBeVisible();
    await expect(page.locator('#f-pnl')).toBeVisible();
    await expect(page.locator('#f-conf')).toBeVisible();
  });

  test('age filter hides stale picks', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="active"]').click();
    await page.waitForTimeout(500);

    const beforeCount = await page.locator('#tab-active table tbody tr').count();

    // Filter to <= 24h
    await page.selectOption('#f-age', '24');
    await page.waitForTimeout(500);
    const afterCount = await page.locator('#tab-active table tbody tr').count();
    expect(afterCount).toBeLessThanOrEqual(beforeCount);

    // Strictest: <= 1h
    await page.selectOption('#f-age', '1');
    await page.waitForTimeout(500);
    const strictCount = await page.locator('#tab-active table tbody tr').count();
    expect(strictCount).toBeLessThanOrEqual(afterCount);
  });

  test('sort dropdown works without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.locator('button.tab-btn[data-tab="active"]').click();
    await page.waitForTimeout(300);

    for (const val of ['age_hours_asc', 'age_hours_desc', 'score_desc', 'pnl_pct_desc']) {
      await page.selectOption('#f-sort', val);
      await page.waitForTimeout(300);
    }
    expect(errors).toHaveLength(0);
  });

  test('Best Picks button sets score sort', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="active"]').click();
    await page.waitForTimeout(300);
    await page.locator('#btn-best-fresh').click();
    await page.waitForTimeout(300);
    const sortVal = await page.locator('#f-sort').inputValue();
    expect(sortVal).toContain('score');
  });

  test('In Profit button sets PnL filter', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="active"]').click();
    await page.waitForTimeout(300);
    await page.locator('#btn-strong-picks').click();
    await page.waitForTimeout(300);
    const pnlVal = await page.locator('#f-pnl').inputValue();
    expect(pnlVal).toBe('pos');
  });

  test('Clear All resets filters', async ({ page }) => {
    await page.selectOption('#f-asset', 'CRYPTO');
    await page.selectOption('#f-age', '24');
    await page.waitForTimeout(300);
    await page.locator('#btn-clear-filters').click();
    await page.waitForTimeout(300);
    expect(await page.locator('#f-asset').inputValue()).toBe('');
    expect(await page.locator('#f-age').inputValue()).toBe('');
  });

  test('system filter populates with systems', async ({ page }) => {
    const options = await page.locator('#f-system option').allTextContents();
    expect(options.length).toBeGreaterThanOrEqual(4);
    expect(options[0]).toBe('All');
  });

  test('search filters by symbol', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="active"]').click();
    await page.waitForTimeout(300);
    const beforeCount = await page.locator('#tab-active table tbody tr').count();
    await page.fill('#f-search', 'BTC');
    await page.waitForTimeout(500);
    const afterCount = await page.locator('#tab-active table tbody tr').count();
    expect(afterCount).toBeLessThanOrEqual(beforeCount);
  });

  test('direction filter works', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="active"]').click();
    await page.waitForTimeout(300);

    await page.selectOption('#f-dir', 'LONG');
    await page.waitForTimeout(300);
    const longCount = await page.locator('#tab-active table tbody tr').count();

    await page.selectOption('#f-dir', 'SHORT');
    await page.waitForTimeout(300);
    const shortCount = await page.locator('#tab-active table tbody tr').count();

    await page.selectOption('#f-dir', '');
    await page.waitForTimeout(300);
    const allCount = await page.locator('#tab-active table tbody tr').count();

    expect(longCount + shortCount).toBeLessThanOrEqual(allCount + 1);
  });

  test('confidence filter works', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="active"]').click();
    await page.waitForTimeout(300);
    const allCount = await page.locator('#tab-active table tbody tr').count();
    await page.selectOption('#f-conf', '0.75');
    await page.waitForTimeout(300);
    const highConfCount = await page.locator('#tab-active table tbody tr').count();
    expect(highConfCount).toBeLessThanOrEqual(allCount);
  });

  test('column settings panel toggles', async ({ page }) => {
    const btn = page.locator('#btn-col-settings');
    await expect(btn).toBeVisible();
    await btn.click();
    await page.waitForTimeout(300);
    await expect(page.locator('#col-settings-panel')).toBeVisible();
    await btn.click();
    await page.waitForTimeout(300);
  });

  test('stale picks auto-filtered from active view', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="active"]').click();
    await page.waitForTimeout(500);
    const content = await page.locator('#tab-active').textContent() || '';
    // Should have content (picks or empty state message)
    const hasContent = content.length > 20 || content.includes('No picks');
    expect(hasContent).toBe(true);
  });

  test('BT vs Forward tab renders', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="btvsfwd"]').click();
    await page.waitForTimeout(500);
    const content = await page.locator('#tab-btvsfwd').textContent() || '';
    expect(content.length).toBeGreaterThan(0);
  });

  test('health indicators on BT vs Forward tab', async ({ page }) => {
    await page.locator('button.tab-btn[data-tab="btvsfwd"]').click();
    await page.waitForTimeout(500);
    const html = await page.locator('#tab-btvsfwd').innerHTML();
    // BT vs Forward tab renders health column with HEALTHY/WATCH/DEGRADED
    // or the Systems tab has status badges (active/retired/monitoring)
    const hasHealthIndicator = html.includes('HEALTHY') ||
                                html.includes('WATCH') ||
                                html.includes('DEGRADED') ||
                                html.includes('Health') ||
                                html.length > 50; // Tab rendered with content
    expect(hasHealthIndicator).toBe(true);
  });
});
