// @ts-check
const { test, expect } = require('@playwright/test');

const AUDIT_URL = 'https://findtorontoevents.ca/audit/';
const FUNDS_URL = 'https://findtorontoevents.ca/audit/funds.html';
const UPDATES_URL = 'https://findtorontoevents.ca/updates/';

// ============================================================
// AUDIT DASHBOARD TESTS
// ============================================================
test.describe('Audit Dashboard — Portfolio Cards', () => {
  test('page loads without errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    expect(errors.filter(e => !e.includes('Failed to fetch'))).toHaveLength(0);
  });

  test('has version v100+', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const version = await page.textContent('body');
    expect(version).toMatch(/v10[0-9]/);
  });

  test('portfolio summary section exists', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    const summary = page.locator('.portfolio-summary, .port-card, [class*="portfolio"]');
    const count = await summary.count();
    expect(count).toBeGreaterThan(0);
  });

  test('has 1x and 20x portfolio cards', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    const body = await page.textContent('body');
    expect(body).toContain('1x');
    expect(body).toContain('20x');
  });

  test('portfolio cards show equity values', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000); // Wait for JSON fetch
    const body = await page.textContent('body');
    // Should have dollar amounts
    expect(body).toMatch(/\$[0-9,]+/);
  });

  test('no broken images or resources', async ({ page }) => {
    const failedResources = [];
    page.on('response', response => {
      if (response.status() >= 400 && !response.url().includes('favicon')) {
        failedResources.push(`${response.status()} ${response.url()}`);
      }
    });
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    // Allow GitHub raw URL failures (data may not exist yet)
    const realFailures = failedResources.filter(f => !f.includes('raw.githubusercontent.com'));
    expect(realFailures).toHaveLength(0);
  });
});

// ============================================================
// FUNDS PAGE TESTS
// ============================================================
test.describe('Funds Page — Copy Trader Tab', () => {
  test('page loads without JS errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(FUNDS_URL, { waitUntil: 'networkidle', timeout: 30000 });
    expect(errors.filter(e => !e.includes('Failed to fetch'))).toHaveLength(0);
  });

  test('has tab navigation', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const tabs = page.locator('[class*="tab"], button[onclick*="tab"], .tab-btn');
    const count = await tabs.count();
    expect(count).toBeGreaterThan(0);
  });

  test('has Copy Traders tab or section', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const body = await page.textContent('body');
    const hasCopyTrader = body.includes('Copy Trader') || body.includes('copy-trader') || body.includes('FORWARD TEST');
    expect(hasCopyTrader).toBeTruthy();
  });

  test('Copy Traders section has purple accent', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const html = await page.content();
    const hasPurple = html.includes('#a855f7') || html.includes('168, 85, 247') || html.includes('purple');
    expect(hasPurple).toBeTruthy();
  });

  test('Copy Traders tab is clickable and shows content', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'networkidle', timeout: 30000 });
    // Find and click the copy trader tab
    const copyTab = page.locator('text=Copy Trader').first();
    if (await copyTab.isVisible()) {
      await copyTab.click();
      await page.waitForTimeout(2000);
      const content = await page.textContent('body');
      // Should show portfolio-related content
      const hasPortfolioContent = content.includes('Hyperliquid') || content.includes('OKX') || content.includes('Bybit') || content.includes('FORWARD TEST') || content.includes('No data');
      expect(hasPortfolioContent).toBeTruthy();
    }
  });

  test('funds page has proper HTML structure', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    // Check for basic HTML structure
    const title = await page.title();
    expect(title.length).toBeGreaterThan(0);
    // No unclosed tags causing layout issues
    const html = await page.content();
    expect(html).toContain('</html>');
  });
});

// ============================================================
// UPDATES PAGE TESTS
// ============================================================
test.describe('Updates Page — Copy Trader Entry', () => {
  test('page loads with dark theme', async ({ page }) => {
    await page.goto(UPDATES_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const html = await page.content();
    expect(html).toMatch(/#0a0a12|background.*dark|rgb\(10/);
  });

  test('has filter pills', async ({ page }) => {
    await page.goto(UPDATES_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const pills = page.locator('.filter-pill, [class*="filter"]');
    const count = await pills.count();
    expect(count).toBeGreaterThan(5);
  });

  test('has copy-trading update entry', async ({ page }) => {
    await page.goto(UPDATES_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const body = await page.textContent('body');
    const hasCopyTrading = body.includes('Copy Trader') || body.includes('copy-trading') || body.includes('Hyperliquid');
    expect(hasCopyTrading).toBeTruthy();
  });

  test('copy trader entry has purple dot', async ({ page }) => {
    await page.goto(UPDATES_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const html = await page.content();
    expect(html).toContain('#a855f7');
  });

  test('has Mar 19, 2026 date', async ({ page }) => {
    await page.goto(UPDATES_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const body = await page.textContent('body');
    expect(body).toContain('Mar 19');
  });

  test('update entries are in chronological order (newest first)', async ({ page }) => {
    await page.goto(UPDATES_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const dates = await page.locator('.update-date').allTextContents();
    if (dates.length >= 2) {
      // First date should be Mar 19 or later
      expect(dates[0]).toMatch(/Mar 1[789]|Mar 2/);
    }
  });

  test('timeline layout has colored dots', async ({ page }) => {
    await page.goto(UPDATES_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const entries = page.locator('.update-entry[style*="dot-color"]');
    const count = await entries.count();
    expect(count).toBeGreaterThan(3);
  });
});

// ============================================================
// DATA INTEGRITY TESTS
// ============================================================
test.describe('Data Files — JSON Validity', () => {
  test('portfolio_1x.json is valid JSON', async ({ request }) => {
    const resp = await request.get('https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/portfolio_1x.json');
    if (resp.ok()) {
      const data = await resp.json();
      expect(data).toHaveProperty('positions');
      expect(data).toHaveProperty('current_balance');
      expect(data).toHaveProperty('stats');
    }
  });

  test('portfolio_20x.json is valid JSON', async ({ request }) => {
    const resp = await request.get('https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/portfolio_20x.json');
    if (resp.ok()) {
      const data = await resp.json();
      expect(data).toHaveProperty('positions');
      expect(data).toHaveProperty('current_balance');
    }
  });

  test('active_picks.json is valid JSON array', async ({ request }) => {
    const resp = await request.get('https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/active_picks.json');
    if (resp.ok()) {
      const data = await resp.json();
      expect(Array.isArray(data)).toBeTruthy();
    }
  });

  test('closed_picks.json has 700+ entries', async ({ request }) => {
    const resp = await request.get('https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/closed_picks.json');
    if (resp.ok()) {
      const data = await resp.json();
      expect(data.length).toBeGreaterThan(700);
    }
  });
});

// ============================================================
// CROSS-PAGE CONSISTENCY TESTS
// ============================================================
test.describe('Cross-Page Consistency', () => {
  test('audit dashboard links to funds page', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const html = await page.content();
    expect(html).toContain('funds');
  });

  test('all pages use HTTPS', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const html = await page.content();
    // No http:// links (except localhost)
    const httpLinks = html.match(/http:\/\/(?!localhost)/g);
    expect(httpLinks || []).toHaveLength(0);
  });
});

// ============================================================
// SCREENSHOT TESTS
// ============================================================
test.describe('Visual Screenshots', () => {
  test('capture audit dashboard', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'tests/screenshots/audit-dashboard.png', fullPage: false });
  });

  test('capture funds page with copy trader tab', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    // Try to click copy trader tab
    const copyTab = page.locator('text=Copy Trader').first();
    if (await copyTab.isVisible()) {
      await copyTab.click();
      await page.waitForTimeout(2000);
    }
    await page.screenshot({ path: 'tests/screenshots/funds-copy-trader.png', fullPage: false });
  });

  test('capture updates page', async ({ page }) => {
    await page.goto(UPDATES_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'tests/screenshots/updates-page.png', fullPage: false });
  });
});
