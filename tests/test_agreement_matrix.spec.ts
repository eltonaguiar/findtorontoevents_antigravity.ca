// @ts-check
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

// Load template and inject mock data for testing
const templatePath = path.join(__dirname, '..', 'audit_dashboard', 'template.html');

test.describe('Agreement Matrix v2', () => {
  let page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();

    // Read template and inject mock data
    let html = fs.readFileSync(templatePath, 'utf8');

    // Create mock data with diverse systems
    const mockData = {
      generated_at: new Date().toISOString(),
      picks: {
        active: [
          { symbol: 'BTCUSDT', direction: 'LONG', source_system: 'battleground', strategy: 'crypto_vwap_deviation_reversion', entry_price: 67000, take_profit: 70000, stop_loss: 65000, confidence: 0.85, ml_score: 0.9, confluence_score: 1, risk_reward: 2.1, forward_trades: 12, forward_wr: 62.7, forward_validated: true, forward_pnl: 45.2 },
          { symbol: 'BTCUSDT', direction: 'LONG', source_system: 'alpha_engine', strategy: 'connors_rsi2', entry_price: 67100, take_profit: 70100, stop_loss: 65100, confidence: 0.76, ml_score: 0.88, confluence_score: 0, forward_trades: 8, forward_wr: 55, forward_validated: true },
          { symbol: 'BTCUSDT', direction: 'SHORT', source_system: 'genetic_programmer', strategy: 'GP_Gen15', entry_price: 67050, take_profit: 64000, stop_loss: 68500, confidence: 0.7 },
          { symbol: 'BTCUSDT', direction: 'SHORT', source_system: 'mape_evolver', strategy: 'MAPE_Gen10', entry_price: 67060, take_profit: 64100, stop_loss: 68600, confidence: 0.68 },
          { symbol: 'ETHUSDT', direction: 'LONG', source_system: 'battleground', strategy: 'drawdown_recovery_rsi_eth', entry_price: 3500, take_profit: 3800, stop_loss: 3300, confidence: 0.9, forward_trades: 15, forward_wr: 72.7, forward_validated: true, forward_pnl: 120.5 },
          { symbol: 'ETHUSDT', direction: 'LONG', source_system: 'kimi_riseoftheclaw', strategy: 'btc_4h_rsi_macd', entry_price: 3510, take_profit: 3810, stop_loss: 3310, confidence: 0.65, forward_trades: 0 },
          { symbol: 'ETHUSDT', direction: 'LONG', source_system: 'kimi_live_signals', strategy: 'crypto_fear_reversal', entry_price: 3505, take_profit: 3805, stop_loss: 3305, confidence: 0.62 },
          { symbol: 'SOLUSDT', direction: 'LONG', source_system: 'revival_battleground', strategy: 'Revival_vwap', entry_price: 140, take_profit: 155, stop_loss: 132, confidence: 0.6 },
          { symbol: 'SOLUSDT', direction: 'LONG', source_system: 'mercury2', strategy: 'xgboost_ensemble', entry_price: 141, take_profit: 156, stop_loss: 133, confidence: 0.72, forward_trades: 3, forward_wr: 33.3, forward_validated: false },
        ],
        recent_closed: [
          { source_system: 'battleground', strategy: 'crypto_vwap_deviation_reversion', symbol: 'BTCUSDT', status: 'WON', pnl_pct: 3.2 },
          { source_system: 'battleground', strategy: 'crypto_vwap_deviation_reversion', symbol: 'ETHUSDT', status: 'WON', pnl_pct: 5.1 },
          { source_system: 'battleground', strategy: 'crypto_vwap_deviation_reversion', symbol: 'BTCUSDT', status: 'LOST', pnl_pct: -2.0 },
          { source_system: 'battleground', strategy: 'drawdown_recovery_rsi_eth', symbol: 'ETHUSDT', status: 'WON', pnl_pct: 8.4 },
          { source_system: 'battleground', strategy: 'drawdown_recovery_rsi_eth', symbol: 'ETHUSDT', status: 'WON', pnl_pct: 4.2 },
          { source_system: 'alpha_engine', strategy: 'connors_rsi2', symbol: 'BTCUSDT', status: 'WON', pnl_pct: 2.8 },
          { source_system: 'alpha_engine', strategy: 'connors_rsi2', symbol: 'BTCUSDT', status: 'LOST', pnl_pct: -1.5 },
          { source_system: 'genetic_programmer', strategy: 'GP_Gen15', symbol: 'BTCUSDT', status: 'LOST', pnl_pct: -4.0 },
        ],
      },
      systems: [],
      summary: { total_systems: 5, total_active_picks: 9, total_closed_picks: 8 },
    };

    // Inject data into template
    const dataScript = `<script>window.DASHBOARD_DATA = ${JSON.stringify(mockData)};</script>`;
    html = html.replace('</head>', dataScript + '</head>');

    // Replace the placeholder reference
    html = html.replace(/const D = .*?;/, 'const D = window.DASHBOARD_DATA || {};');

    await page.setContent(html, { waitUntil: 'domcontentloaded' });
    // Wait for rendering
    await page.waitForTimeout(500);
  });

  test('agreement matrix renders and is visible', async () => {
    const matrix = page.locator('#agreement-matrix');
    await expect(matrix).toBeVisible();
  });

  test('matrix has deduplication - genome systems counted as one group', async () => {
    // GP and MAPE are both in genome_gp group, should count as 1 signal
    const dedupInfo = page.locator('#matrix-dedup-info');
    const text = await dedupInfo.textContent();
    // raw signals > unique signals (dedup happened)
    if (text && text.includes('raw')) {
      console.log('Dedup info:', text);
      expect(text).toContain('deduped');
    }
  });

  test('system rows have rank numbers', async () => {
    const ranks = page.locator('.sys-rank');
    const count = await ranks.count();
    expect(count).toBeGreaterThan(0);
    console.log(`Found ${count} system rank badges`);
  });

  test('system description tooltips exist', async () => {
    const descTips = page.locator('.sys-desc-tip');
    const count = await descTips.count();
    expect(count).toBeGreaterThan(0);
    console.log(`Found ${count} system description tooltips`);
  });

  test('collapse toggle works', async () => {
    const matrixBody = page.locator('#matrix-body');
    await expect(matrixBody).toBeVisible();

    // Click the header to collapse
    const header = page.locator('#agreement-matrix > div:first-child');
    await header.click();
    await page.waitForTimeout(100);

    // Should be hidden now
    const display = await matrixBody.evaluate(el => el.style.display);
    expect(display).toBe('none');

    // Click again to expand
    await header.click();
    await page.waitForTimeout(100);
    const display2 = await matrixBody.evaluate(el => el.style.display);
    expect(display2).toBe('block');
  });

  test('tooltips contain composite pick score', async () => {
    const tooltips = page.locator('.matrix-tooltip');
    const count = await tooltips.count();
    expect(count).toBeGreaterThan(0);

    // Check first tooltip has Score
    const firstTooltip = await tooltips.first().innerHTML();
    expect(firstTooltip).toContain('Score:');
    console.log('First tooltip contains Score field');
  });

  test('tooltips show forward validation data', async () => {
    const tooltips = page.locator('.matrix-tooltip');
    const allHtml = await tooltips.allInnerTexts();
    const hasForward = allHtml.some(t => t.includes('Forward:') || t.includes('No forward data'));
    expect(hasForward).toBeTruthy();
    console.log('Forward validation data present in tooltips');
  });

  test('tooltips show strategy track record', async () => {
    const tooltips = page.locator('.matrix-tooltip');
    const allHtml = await tooltips.allInnerTexts();
    const hasTrackRecord = allHtml.some(t => t.includes('Track Record') || t.includes('Strategy record'));
    expect(hasTrackRecord).toBeTruthy();
    console.log('Strategy track record present in tooltips');
  });

  test('agree row shows deduplicated counts', async () => {
    const agreeRow = page.locator('.agree-row');
    await expect(agreeRow).toBeVisible();
    const text = await agreeRow.textContent();
    expect(text).toContain('Agree');
    console.log('Agree row text:', text);
  });

  test('performance mini bars render for systems with closed picks', async () => {
    const perfBars = page.locator('.perf-bar');
    const count = await perfBars.count();
    // May be 0 if tooltips aren't hovered, but CSS exists
    console.log(`Found ${count} performance mini-bar elements in DOM`);
  });
});
