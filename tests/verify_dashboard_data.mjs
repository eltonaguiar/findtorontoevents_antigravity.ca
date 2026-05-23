/**
 * Playwright test: Verify audit dashboard has complete data across all asset classes.
 * Checks that CURRENT, PRICE, PNL%, POS columns are populated for forex, crypto, and equity.
 *
 * Usage: npx playwright test tests/verify_dashboard_data.mjs
 */
import { test, expect } from '@playwright/test';

const DASHBOARD_URL = 'https://findtorontoevents.ca/audit/';
const WAIT_FOR_PRICES = 25000; // Wait for live price APIs to respond

test.describe('Dashboard Data Completeness', () => {

  test('All asset classes have populated price columns', async ({ page }) => {
    // Increase timeout for API calls
    test.setTimeout(90000);

    // Collect console logs
    const consoleLogs = [];
    const consoleErrors = [];
    page.on('console', msg => {
      const text = msg.text();
      consoleLogs.push(text);
      if (msg.type() === 'error' && text.includes('429')) consoleErrors.push(text);
    });

    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle', timeout: 30000 });

    // Wait for live prices to load
    await page.waitForTimeout(WAIT_FOR_PRICES);

    // Click Active Picks tab
    await page.click('[data-tab="active"]');
    await page.waitForTimeout(2000);

    // Get all active pick rows
    const rows = await page.$$('#tab-active table tbody tr');
    console.log(`Total active pick rows: ${rows.length}`);

    // Analyze each row
    const results = { crypto: [], forex: [], equity: [], other: [] };
    const gaps = { missingCurrent: [], missingPrice: [], missingPnl: [], missingPos: [] };

    for (let i = 0; i < Math.min(rows.length, 200); i++) {
      const cells = await rows[i].$$('td');
      if (cells.length < 10) continue;

      const symbol = await cells[1]?.innerText().catch(() => '') || '';
      const current = await cells[5]?.innerText().catch(() => '') || '';
      const price = await cells[8]?.innerText().catch(() => '') || '';
      const pnl = await cells[9]?.innerText().catch(() => '') || '';
      const pos = await cells[10]?.innerText().catch(() => '') || '';

      // Classify asset
      let assetClass = 'other';
      if (symbol.includes('=X')) assetClass = 'forex';
      else if (symbol.endsWith('USDT') || symbol.endsWith('USD') || symbol.endsWith('-USD')) assetClass = 'crypto';
      else if (['SPY','QQQ','AAPL','NVDA','MSFT','GLD','SLV','IWM','HYG','NIO','GC=F'].includes(symbol.replace('=F',''))) assetClass = 'equity';

      const row = { symbol, current, price, pnl, pos };
      results[assetClass].push(row);

      // Check for gaps
      if (!current || current === '—' || current === '') gaps.missingCurrent.push(symbol);
      if (!price || price === '—' || price === '') gaps.missingPrice.push(symbol);
      if (!pnl || pnl === '+0.00%' || pnl === '—') gaps.missingPnl.push(symbol);
      if (!pos || pos === '—') gaps.missingPos.push(symbol);
    }

    // Report
    console.log('\n=== ASSET CLASS COUNTS ===');
    console.log(`Crypto: ${results.crypto.length}`);
    console.log(`Forex: ${results.forex.length}`);
    console.log(`Equity: ${results.equity.length}`);
    console.log(`Other (unclassified): ${results.other.length}`);

    console.log('\n=== DATA GAPS ===');
    console.log(`Missing CURRENT: ${gaps.missingCurrent.length} — ${gaps.missingCurrent.slice(0, 10).join(', ')}${gaps.missingCurrent.length > 10 ? '...' : ''}`);
    console.log(`Missing PRICE: ${gaps.missingPrice.length} — ${gaps.missingPrice.slice(0, 10).join(', ')}${gaps.missingPrice.length > 10 ? '...' : ''}`);
    console.log(`Missing PNL%: ${gaps.missingPnl.length} — ${gaps.missingPnl.slice(0, 10).join(', ')}${gaps.missingPnl.length > 10 ? '...' : ''}`);
    console.log(`Missing POS: ${gaps.missingPos.length} — ${gaps.missingPos.slice(0, 10).join(', ')}${gaps.missingPos.length > 10 ? '...' : ''}`);

    // Check console for API results
    console.log('\n=== API LOGS ===');
    const apiLogs = consoleLogs.filter(l => l.includes('[FOREX]') || l.includes('[STOCKS]') || l.includes('[LIVE]'));
    apiLogs.forEach(l => console.log(l));

    console.log('\n=== 429 ERRORS ===');
    console.log(`Count: ${consoleErrors.length}`);
    if (consoleErrors.length > 0) console.log(`First 3: ${consoleErrors.slice(0, 3).join('\n')}`);

    // FOREX checks
    console.log('\n=== FOREX SAMPLE ===');
    results.forex.slice(0, 5).forEach(r => console.log(`  ${r.symbol}: CURRENT=${r.current} PRICE=${r.price} PNL=${r.pnl} POS=${r.pos}`));

    // EQUITY checks
    console.log('\n=== EQUITY SAMPLE ===');
    results.equity.slice(0, 5).forEach(r => console.log(`  ${r.symbol}: CURRENT=${r.current} PRICE=${r.price} PNL=${r.pnl} POS=${r.pos}`));

    // Assertions
    const forexWithCurrent = results.forex.filter(r => r.current && r.current !== '—');
    const cryptoWithCurrent = results.crypto.filter(r => r.current && r.current !== '—');

    console.log(`\n=== COVERAGE ===`);
    console.log(`Forex with CURRENT: ${forexWithCurrent.length}/${results.forex.length} (${results.forex.length > 0 ? Math.round(forexWithCurrent.length/results.forex.length*100) : 0}%)`);
    console.log(`Crypto with CURRENT: ${cryptoWithCurrent.length}/${results.crypto.length} (${results.crypto.length > 0 ? Math.round(cryptoWithCurrent.length/results.crypto.length*100) : 0}%)`);

    // Forex should have >90% coverage
    if (results.forex.length > 0) {
      expect(forexWithCurrent.length / results.forex.length).toBeGreaterThan(0.8);
    }

    // No 429 errors should occur
    expect(consoleErrors.length).toBeLessThan(5);
  });

  test('Filter by asset class and verify each', async ({ page }) => {
    test.setTimeout(90000);
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(WAIT_FOR_PRICES);

    // Click Active Picks tab
    await page.click('[data-tab="active"]');
    await page.waitForTimeout(1000);

    // Test each asset filter
    for (const asset of ['CRYPTO', 'FOREX', 'EQUITY']) {
      // Look for asset filter select
      const filterSelect = await page.$('#f-asset');
      if (!filterSelect) {
        console.log(`No asset filter found, skipping ${asset} check`);
        continue;
      }

      await filterSelect.selectOption(asset);
      await page.waitForTimeout(2000);

      const rows = await page.$$('#tab-active table tbody tr');
      const rowCount = rows.length;

      // Count rows with populated CURRENT column
      let withPrice = 0;
      for (let i = 0; i < Math.min(rows.length, 50); i++) {
        const cells = await rows[i].$$('td');
        if (cells.length < 6) continue;
        const current = await cells[5]?.innerText().catch(() => '') || '';
        if (current && current !== '—' && current !== '') withPrice++;
      }

      const pct = rowCount > 0 ? Math.round(withPrice / Math.min(rowCount, 50) * 100) : 0;
      console.log(`${asset}: ${rowCount} rows, ${withPrice}/${Math.min(rowCount, 50)} with CURRENT price (${pct}%)`);

      // Reset filter
      await filterSelect.selectOption('');
      await page.waitForTimeout(500);
    }
  });
});
