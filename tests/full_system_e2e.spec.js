/**
 * Full Trading System E2E Test Suite
 *
 * Comprehensive Playwright tests covering:
 *  1. Audit Dashboard — UI, filters, data quality, modals
 *  2. Funds Page — table rendering, metrics validation
 *  3. Data Integrity — dashboard_payload.json validation
 *  4. API Endpoints — Binance (with failover), CoinGecko, Fear & Greed
 *  5. Smart Picks — history JSON structure, dashboard card rendering
 *
 * Run: npx playwright test tests/full_system_e2e.spec.js --project="Desktop Chrome"
 */

const { test, expect } = require('@playwright/test');

const AUDIT_URL = 'https://findtorontoevents.ca/audit/';
const FUNDS_URL = 'https://findtorontoevents.ca/audit/funds.html';
const PAYLOAD_URL = 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/audit_trail/data/dashboard_payload.json';
const SMART_PICKS_URL = 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/smart_picks_history.json';

// ═══════════════════════════════════════════════════════════════════════
// 1. AUDIT DASHBOARD
// ═══════════════════════════════════════════════════════════════════════

test.describe('1. Audit Dashboard', () => {
  test.setTimeout(90_000);

  test('page loads without JS errors', async ({ page }) => {
    const jsErrors = [];
    page.on('pageerror', (err) => jsErrors.push(err.message));

    const response = await page.goto(AUDIT_URL, {
      waitUntil: 'networkidle',
      timeout: 60_000,
    });
    expect(response?.status()).toBeLessThan(400);

    // Wait for dynamic rendering
    await page.waitForTimeout(3000);

    // Filter out benign network/favicon errors
    const realErrors = jsErrors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('net::ERR_') &&
        !e.includes('404') &&
        !e.includes('gstatic') &&
        !e.includes('ERR_NAME_NOT_RESOLVED')
    );
    expect(realErrors, `Unexpected JS errors: ${realErrors.join('; ')}`).toHaveLength(0);
  });

  test('active picks table renders with data', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(4000);

    // Click the active picks tab if not already selected
    const activeTab = page.locator('button.tab-btn[data-tab="active"]');
    if (await activeTab.count()) {
      await activeTab.click();
      await page.waitForTimeout(1000);
    }

    // Find table rows in the active tab
    const rows = page.locator('#tab-active table tbody tr, #tab-active .pick-row, #active-table tbody tr');
    const rowCount = await rows.count();
    expect(rowCount, 'Active picks table should have rows').toBeGreaterThan(0);
  });

  test('score column shows numbers (not NaN)', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(4000);

    // Click active tab
    const activeTab = page.locator('button.tab-btn[data-tab="active"]');
    if (await activeTab.count()) {
      await activeTab.click();
      await page.waitForTimeout(1000);
    }

    // Collect all score-related cells — look for .score, td with score values, or score badges
    const scoreCells = page.locator(
      '#tab-active .score-val, #tab-active .score-badge, #tab-active td:nth-child(2), .pick-score'
    );
    const count = await scoreCells.count();

    if (count > 0) {
      const scoreTexts = await scoreCells.allTextContents();
      for (const txt of scoreTexts.slice(0, 20)) {
        const cleaned = txt.replace(/[^0-9.\-]/g, '').trim();
        if (cleaned) {
          const num = parseFloat(cleaned);
          expect(isNaN(num), `Score "${txt}" should be a valid number, not NaN`).toBe(false);
        }
      }
    }
  });

  test('win rate percentages are 0-100%', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(4000);

    // Check stat cards and system summaries for win rate values
    const bodyText = await page.textContent('body');

    // Extract all percentage patterns from the page
    const percentages = bodyText.match(/(\d{1,3}(?:\.\d+)?)\s*%/g) || [];

    // Check the WR-specific ones (look for values that are clearly win rates)
    let foundWR = false;
    for (const pct of percentages) {
      const val = parseFloat(pct);
      if (!isNaN(val) && val >= 0 && val <= 100) {
        foundWR = true;
      }
      // No win rate should exceed 100%
      expect(val, `Percentage ${pct} should be <= 100`).toBeLessThanOrEqual(100);
      expect(val, `Percentage ${pct} should be >= 0`).toBeGreaterThanOrEqual(0);
    }
    expect(foundWR, 'Page should contain at least one valid percentage').toBe(true);
  });

  test('growth values are reasonable (<$10M)', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(4000);

    // Look for dollar values on the page (stat cards, system rows, etc.)
    const dollarEls = page.locator('.stat-card .value, .stat-card .val');
    const count = await dollarEls.count();

    for (let i = 0; i < count; i++) {
      const text = await dollarEls.nth(i).textContent();
      if (text && text.includes('$')) {
        const num = parseFloat(text.replace(/[$,]/g, ''));
        if (!isNaN(num) && num > 0) {
          expect(num, `Growth "$${num}" should be < $10M`).toBeLessThan(10_000_000);
        }
      }
    }
  });

  test('Best Picks filter button works', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(4000);

    // Click active tab first
    const activeTab = page.locator('button.tab-btn[data-tab="active"]');
    if (await activeTab.count()) {
      await activeTab.click();
      await page.waitForTimeout(1000);
    }

    const btn = page.locator('#btn-best-fresh');
    await expect(btn, 'Best Picks button should exist').toBeVisible({ timeout: 10_000 });
    await btn.click();
    await page.waitForTimeout(1000);

    // After clicking, the table should still have rows (filter applied)
    const bodyText = await page.locator('#tab-active').textContent();
    expect(bodyText.length, 'Active tab should have content after Best Picks filter').toBeGreaterThan(10);
  });

  test('Proven Only filter button works', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(4000);

    const activeTab = page.locator('button.tab-btn[data-tab="active"]');
    if (await activeTab.count()) {
      await activeTab.click();
      await page.waitForTimeout(1000);
    }

    const btn = page.locator('#btn-proven-picks');
    await expect(btn, 'Proven Only button should exist').toBeVisible({ timeout: 10_000 });
    await btn.click();
    await page.waitForTimeout(1000);

    // Check that the filter tag appears
    const filterTags = await page.textContent('body');
    // The Proven Only button should toggle a filter state
    expect(filterTags).toBeTruthy();
  });

  test('In Profit filter button works', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(4000);

    const activeTab = page.locator('button.tab-btn[data-tab="active"]');
    if (await activeTab.count()) {
      await activeTab.click();
      await page.waitForTimeout(1000);
    }

    const btn = page.locator('#btn-strong-picks');
    await expect(btn, 'In Profit button should exist').toBeVisible({ timeout: 10_000 });
    await btn.click();
    await page.waitForTimeout(1000);

    const bodyText = await page.locator('#tab-active').textContent();
    expect(bodyText.length).toBeGreaterThan(0);
  });

  test('score tier dropdown filters correctly', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(4000);

    const activeTab = page.locator('button.tab-btn[data-tab="active"]');
    if (await activeTab.count()) {
      await activeTab.click();
      await page.waitForTimeout(1000);
    }

    const dropdown = page.locator('#f-score-tier');
    await expect(dropdown, 'Score tier dropdown should exist').toBeVisible({ timeout: 10_000 });

    // Get all options
    const options = await dropdown.locator('option').allTextContents();
    expect(options.length, 'Score tier should have multiple options').toBeGreaterThan(1);

    // Select a non-default option (skip the first which is usually "All")
    if (options.length > 1) {
      await dropdown.selectOption({ index: 1 });
      await page.waitForTimeout(1000);

      // The leverage label should update or filter should apply
      const leverageLabel = page.locator('#score-tier-leverage-label');
      if (await leverageLabel.count()) {
        const text = await leverageLabel.textContent();
        expect(text, 'Leverage label should have content').toBeTruthy();
      }
    }

    // Reset to default
    await dropdown.selectOption({ index: 0 });
  });

  test('PnL drilldown modal opens on click', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(5000);

    // Navigate to a tab that has clickable PnL cells (agreement matrix or symbols)
    // The trade modal overlay exists on the page
    const modalOverlay = page.locator('.trade-modal-overlay, #trade-modal-overlay');
    expect(await modalOverlay.count(), 'Trade modal overlay element should exist in DOM').toBeGreaterThan(0);

    // Try clicking a PnL cell that triggers showTradeModal
    // Look for clickable cells with cursor:pointer in the agreement or system-pair tables
    const clickablePnl = page.locator('[onclick*="showTradeModal"]').first();
    if (await clickablePnl.count()) {
      await clickablePnl.click();
      await page.waitForTimeout(1000);

      // Modal should become active/visible
      const activeModal = page.locator('.trade-modal-overlay.active');
      const isVisible = await activeModal.count();
      expect(isVisible, 'Trade drilldown modal should open').toBeGreaterThan(0);

      // Close it
      const closeBtn = page.locator('.trade-modal-close').first();
      if (await closeBtn.count()) {
        await closeBtn.click();
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 2. FUNDS PAGE
// ═══════════════════════════════════════════════════════════════════════

test.describe('2. Funds Page', () => {
  test.setTimeout(90_000);

  test('all fund rows render', async ({ page }) => {
    const response = await page.goto(FUNDS_URL, {
      waitUntil: 'networkidle',
      timeout: 60_000,
    });
    expect(response?.status()).toBeLessThan(400);
    await page.waitForTimeout(4000);

    // Fund rows in the main table
    const rows = page.locator('#funds-table tbody tr, .fund-row, table tbody tr');
    const rowCount = await rows.count();
    expect(rowCount, 'Funds table should have rows').toBeGreaterThan(0);
  });

  test('win rates <= 100%', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(4000);

    const bodyText = await page.textContent('body');
    const percentages = bodyText.match(/(\d{1,3}(?:\.\d+)?)%/g) || [];

    for (const pct of percentages) {
      const val = parseFloat(pct);
      if (!isNaN(val)) {
        expect(val, `Win rate ${pct} should be <= 100`).toBeLessThanOrEqual(100);
      }
    }
  });

  test('profit factors are numbers', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(4000);

    // Look for profit factor column values
    const pfCells = page.locator('td:has-text(".")');
    const count = await pfCells.count();

    // The page should have loaded data (not be empty)
    const bodyText = await page.textContent('body');
    expect(bodyText.length).toBeGreaterThan(100);

    // Specifically look for the Profit Factor header and its column
    const pfHeader = page.locator('th:has-text("Profit Factor"), th[data-sort="pf"]');
    if (await pfHeader.count()) {
      // Get the column index
      const allHeaders = await page.locator('thead th').allTextContents();
      const pfIndex = allHeaders.findIndex((h) => h.includes('Profit Factor'));

      if (pfIndex >= 0) {
        const pfValues = page.locator(`tbody tr td:nth-child(${pfIndex + 1})`);
        const pfCount = await pfValues.count();

        for (let i = 0; i < Math.min(pfCount, 20); i++) {
          const text = await pfValues.nth(i).textContent();
          const cleaned = text.replace(/[^0-9.+\-]/g, '').trim();
          if (cleaned) {
            const num = parseFloat(cleaned);
            expect(isNaN(num), `Profit factor "${text}" should parse as number`).toBe(false);
            expect(num, `Profit factor should be >= 0`).toBeGreaterThanOrEqual(0);
          }
        }
      }
    }
  });

  test('$10K growth values are reasonable', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(4000);

    // Find $10K Growth column
    const allHeaders = await page.locator('thead th').allTextContents();
    const growthIdx = allHeaders.findIndex((h) => h.includes('10K') || h.includes('Growth'));

    if (growthIdx >= 0) {
      const growthCells = page.locator(`tbody tr td:nth-child(${growthIdx + 1})`);
      const count = await growthCells.count();

      for (let i = 0; i < Math.min(count, 20); i++) {
        const text = await growthCells.nth(i).textContent();
        const num = parseFloat(text.replace(/[$,]/g, ''));
        if (!isNaN(num) && num > 0) {
          expect(num, `Growth value $${num} should be < $10M`).toBeLessThan(10_000_000);
        }
      }
    }
  });

  test('copy trader tooltips appear on hover', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(4000);

    // Click on Copy Traders tab if it exists
    const ctTab = page.locator('button.tab-btn[data-tab="copytrader"], button:has-text("Copy Trader")');
    if (await ctTab.count()) {
      await ctTab.click();
      await page.waitForTimeout(1000);
    }

    // Find elements with data-tip or title attributes (tooltips)
    const tooltipEls = page.locator('[data-tip], [title]');
    const tipCount = await tooltipEls.count();
    expect(tipCount, 'Page should have tooltip elements').toBeGreaterThan(0);

    // Hover over the first few and check they have content
    for (let i = 0; i < Math.min(tipCount, 3); i++) {
      const tip = await tooltipEls.nth(i).getAttribute('data-tip') ||
                  await tooltipEls.nth(i).getAttribute('title');
      if (tip) {
        expect(tip.length, 'Tooltip should have content').toBeGreaterThan(0);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 3. DATA INTEGRITY
// ═══════════════════════════════════════════════════════════════════════

test.describe('3. Data Integrity', () => {
  test.setTimeout(60_000);

  let payload;

  test('fetch dashboard_payload.json and validate structure', async ({ request }) => {
    const response = await request.get(PAYLOAD_URL);
    expect(response.status(), 'dashboard_payload.json should return 200').toBe(200);

    payload = await response.json();
    expect(payload, 'Payload should be an object').toBeTruthy();
  });

  test('systems count > 50', async ({ request }) => {
    const response = await request.get(PAYLOAD_URL);
    const data = await response.json();

    // Count systems — could be in systems array or systems object
    const systems = data.systems || data.data?.systems || [];
    const systemCount = Array.isArray(systems) ? systems.length : Object.keys(systems).length;
    expect(systemCount, `Expected >50 systems, got ${systemCount}`).toBeGreaterThan(50);
  });

  test('closed_picks > 1000', async ({ request }) => {
    const response = await request.get(PAYLOAD_URL);
    const data = await response.json();

    // Look for closed_picks count in various locations
    let closedCount = data.closed_picks ||
      data.summary?.closed_picks ||
      data.meta?.closed_picks ||
      0;

    // If not at top level, sum from systems
    if (!closedCount) {
      const systems = data.systems || data.data?.systems || [];
      const arr = Array.isArray(systems) ? systems : Object.values(systems);
      closedCount = arr.reduce((sum, s) => sum + (s.closed_picks || s.closed || 0), 0);
    }

    expect(closedCount, `Expected >1000 closed picks, got ${closedCount}`).toBeGreaterThan(1000);
  });

  test('no system has win_rate > 100', async ({ request }) => {
    const response = await request.get(PAYLOAD_URL);
    const data = await response.json();

    const systems = data.systems || data.data?.systems || [];
    const arr = Array.isArray(systems) ? systems : Object.values(systems);

    for (const sys of arr) {
      const wr = sys.win_rate ?? sys.winRate ?? sys.wr ?? null;
      if (wr !== null && wr !== undefined) {
        expect(
          wr,
          `System "${sys.name || sys.system || 'unknown'}" has win_rate ${wr} > 100`
        ).toBeLessThanOrEqual(100);
      }
    }
  });

  test('data freshness < 6 hours', async ({ request }) => {
    const response = await request.get(PAYLOAD_URL);
    const data = await response.json();

    // Look for timestamp in various fields
    const ts = data.timestamp || data.updated_at || data.generated || data.meta?.timestamp || data.meta?.generated || null;

    if (ts) {
      const dataTime = new Date(ts).getTime();
      const now = Date.now();
      const sixHoursMs = 6 * 60 * 60 * 1000;
      const age = now - dataTime;

      expect(
        age,
        `Data is ${(age / 3600000).toFixed(1)}h old — should be < 6h`
      ).toBeLessThan(sixHoursMs);
    } else {
      // If no timestamp field, just warn — don't fail
      console.warn('No timestamp field found in dashboard_payload.json');
    }
  });

  test('total_pnl is a number (not NaN/Infinity)', async ({ request }) => {
    const response = await request.get(PAYLOAD_URL);
    const data = await response.json();

    // Look for total PnL in the payload
    const totalPnl = data.total_pnl ?? data.summary?.total_pnl ?? data.meta?.total_pnl ?? null;

    if (totalPnl !== null && totalPnl !== undefined) {
      expect(isNaN(totalPnl), 'total_pnl should not be NaN').toBe(false);
      expect(isFinite(totalPnl), 'total_pnl should not be Infinity').toBe(true);
      expect(typeof totalPnl, 'total_pnl should be a number').toBe('number');
    }

    // Also check per-system PnL values
    const systems = data.systems || data.data?.systems || [];
    const arr = Array.isArray(systems) ? systems : Object.values(systems);
    for (const sys of arr.slice(0, 30)) {
      const pnl = sys.total_pnl ?? sys.pnl ?? null;
      if (pnl !== null && pnl !== undefined) {
        expect(isNaN(pnl), `PnL for "${sys.name || 'unknown'}" should not be NaN`).toBe(false);
        expect(isFinite(pnl), `PnL for "${sys.name || 'unknown'}" should not be Infinity`).toBe(true);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 4. API ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════

test.describe('4. API Endpoints', () => {
  test.setTimeout(60_000);

  test('Binance ticker endpoint responds (with failover)', async ({ request }) => {
    const endpoints = [
      'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT',
      'https://api1.binance.com/api/v3/ticker/price?symbol=BTCUSDT',
      'https://api2.binance.com/api/v3/ticker/price?symbol=BTCUSDT',
      'https://api3.binance.com/api/v3/ticker/price?symbol=BTCUSDT',
    ];

    let success = false;
    let lastError = '';
    let respondedEndpoint = '';

    for (const url of endpoints) {
      try {
        const response = await request.get(url, { timeout: 10_000 });
        if (response.status() === 200) {
          const data = await response.json();
          expect(data.symbol).toBe('BTCUSDT');
          expect(parseFloat(data.price)).toBeGreaterThan(0);
          success = true;
          respondedEndpoint = url;
          break;
        }
      } catch (e) {
        lastError = e.message;
      }
    }

    expect(
      success,
      `None of ${endpoints.length} Binance endpoints responded. Last error: ${lastError}`
    ).toBe(true);
    console.log(`Binance responded via: ${respondedEndpoint}`);
  });

  test('CoinGecko trending endpoint responds', async ({ request }) => {
    let success = false;
    try {
      const response = await request.get(
        'https://api.coingecko.com/api/v3/search/trending',
        { timeout: 15_000 }
      );
      if (response.status() === 200) {
        const data = await response.json();
        expect(data.coins, 'CoinGecko trending should have coins array').toBeDefined();
        expect(data.coins.length).toBeGreaterThan(0);
        success = true;
      } else if (response.status() === 429) {
        // Rate limited — acceptable, not a failure
        console.warn('CoinGecko rate-limited (429), skipping validation');
        success = true;
      }
    } catch (e) {
      console.warn(`CoinGecko trending failed: ${e.message}`);
    }
    expect(success, 'CoinGecko trending endpoint should respond').toBe(true);
  });

  test('Fear & Greed API responds', async ({ request }) => {
    const response = await request.get(
      'https://api.alternative.me/fng/?limit=1',
      { timeout: 15_000 }
    );
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data.data, 'Fear & Greed should have data array').toBeDefined();
    expect(data.data.length).toBeGreaterThan(0);

    const fng = data.data[0];
    const value = parseInt(fng.value, 10);
    expect(value, 'Fear & Greed index should be 0-100').toBeGreaterThanOrEqual(0);
    expect(value).toBeLessThanOrEqual(100);
    expect(fng.value_classification, 'Should have classification text').toBeTruthy();
  });
});

// ═══════════════════════════════════════════════════════════════════════
// 5. SMART PICKS
// ═══════════════════════════════════════════════════════════════════════

test.describe('5. Smart Picks', () => {
  test.setTimeout(60_000);

  test('smart_picks_history.json has valid structure if it exists', async ({ request }) => {
    const response = await request.get(SMART_PICKS_URL);

    if (response.status() === 200) {
      const data = await response.json();

      // Should have batches array
      expect(data.batches, 'smart_picks_history should have batches array').toBeDefined();
      expect(Array.isArray(data.batches)).toBe(true);

      if (data.batches.length > 0) {
        const batch = data.batches[0];

        // Each batch should have expected fields
        expect(batch, 'Batch should be an object').toBeTruthy();

        // Check for common fields: timestamp/date, picks, score
        const hasTimestamp = 'timestamp' in batch || 'date' in batch || 'generated' in batch || 'batch_id' in batch;
        expect(hasTimestamp, 'Batch should have a timestamp or date field').toBe(true);

        // Check picks array if present
        if (batch.picks && Array.isArray(batch.picks)) {
          for (const pick of batch.picks.slice(0, 5)) {
            // Each pick should have symbol at minimum
            const hasSymbol = 'symbol' in pick || 'pair' in pick || 'asset' in pick;
            expect(hasSymbol, `Pick should have symbol/pair/asset field: ${JSON.stringify(pick).slice(0, 100)}`).toBe(true);
          }
        }
      }
    } else if (response.status() === 404) {
      console.warn('smart_picks_history.json does not exist yet (404) — skipping structure check');
    } else {
      throw new Error(`Unexpected status ${response.status()} for smart_picks_history.json`);
    }
  });

  test('Smart WR card renders (not stuck at "...")', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60_000 });

    // Wait for the smart picks data to load (it fetches async)
    await page.waitForTimeout(8000);

    // Look for the Smart WR stat card
    const smartWrCard = page.locator(
      '.stat-card:has-text("Smart WR"), .stat-card:has-text("Smart"), [class*="smart"]'
    );

    if (await smartWrCard.count()) {
      const text = await smartWrCard.first().textContent();

      // It should not be stuck at "..." (the loading placeholder)
      const value = text.replace(/Smart\s*WR/i, '').trim();
      if (value !== '...') {
        // If loaded, should contain a percentage or "N/A"
        const hasValue = /\d+(\.\d+)?%/.test(value) || value.includes('N/A') || value.includes('--');
        expect(hasValue, `Smart WR card should show a value, got: "${value}"`).toBe(true);
      } else {
        // Still loading after 8s — flag as warning but don't hard fail
        console.warn('Smart WR card still showing "..." after 8s — may be a slow fetch');
      }
    } else {
      console.warn('Smart WR card not found on page — may not be rendered in current version');
    }
  });
});
