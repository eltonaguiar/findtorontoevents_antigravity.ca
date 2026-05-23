/**
 * HyroTrader live freshness: verify /audit/hyrotrader/ shows recent data (not stale).
 * Run: VERIFY_REMOTE=1 npx playwright test tests/hyrotrader_live_freshness.spec.ts --project="Desktop Chrome"
 */
import { test, expect } from '@playwright/test';

const LIVE = 'https://findtorontoevents.ca';
const QUAN_JSON = `${LIVE}/audit/data/hyro_quan_bridge.json?cb=${Date.now()}`;
const PICKS_JSON = `${LIVE}/audit/data/hyrotrader_picks.json?cb=${Date.now()}`;
const ENHANCED_JSON = `${LIVE}/audit/data/hyrotrader_enhanced_picks.json?cb=${Date.now()}`;
const LIVE_STRATS_JSON = `${LIVE}/audit/data/hyro_live_strategies.json?cb=${Date.now()}`;
const PAGE_URL = `${LIVE}/audit/hyrotrader/`;

const ALL_15_SYMBOLS = [
  'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'XRPUSDT',
  'BNBUSDT', 'DOGEUSDT', 'LINKUSDT', 'ADAUSDT', 'DOTUSDT',
  'NEARUSDT', 'SUIUSDT', 'ARBUSDT', 'APTUSDT', 'PEPEUSDT',
];

test.describe('HyroTrader live freshness checks', () => {
  test('hyro_quan_bridge.json has recent timestamp (not Apr 7)', async ({ request }) => {
    const res = await request.get(QUAN_JSON);
    expect(res.ok(), `GET quan_bridge must be 200 (got ${res.status()})`).toBe(true);

    const data = await res.json();
    expect(data.generated_at, 'generated_at must exist').toBeTruthy();
    expect(data.fear_greed, 'fear_greed must exist').toBeDefined();

    // Must NOT be the stale Apr 7 data
    const genAt = String(data.generated_at);
    expect(genAt).not.toContain('2026-04-07');

    // Must be from today or recent (within last 48h)
    const genDate = new Date(genAt);
    const now = new Date();
    const ageMs = now.getTime() - genDate.getTime();
    const ageHours = ageMs / (1000 * 60 * 60);
    expect(ageHours, `Data age ${ageHours.toFixed(1)}h should be < 48h`).toBeLessThan(48);

    // Fear & Greed should not be the old value of 11
    expect(data.fear_greed, 'fear_greed should not be stale value 11').not.toBe(11);

    // Must have all 15 symbols
    const symbols = Object.keys(data.symbols || {});
    expect(symbols.length, `should have 15 symbols, got ${symbols.length}`).toBe(15);
    for (const s of ALL_15_SYMBOLS) {
      expect(symbols, `bridge JSON missing ${s}`).toContain(s);
    }
    console.log(`  quan_bridge: generated_at=${genAt}, F&G=${data.fear_greed}, symbols=${symbols.join(',')}`);
  });

  test('hyro_live_strategies.json has 15 symbols and 12 strategies', async ({ request }) => {
    const res = await request.get(LIVE_STRATS_JSON);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    const syms: string[] = data.symbols || [];
    expect(syms.length, `live strategies should have 15 symbols, got ${syms.length}`).toBe(15);
    for (const s of ALL_15_SYMBOLS) {
      expect(syms, `live strategies missing ${s}`).toContain(s);
    }
    // strategies should have no per-symbol restriction (no "symbols" key on proven/promising)
    const strats = data.strategies || [];
    expect(strats.length, 'should have 12 strategies').toBe(12);
    const nonDemoted = strats.filter((s: any) => s.tier !== 'demoted');
    for (const st of nonDemoted) {
      expect(st.symbols, `${st.id} should NOT have per-symbol restriction`).toBeUndefined();
    }
    console.log(`  live_strategies: ${syms.length} symbols, ${strats.length} strategies, all scan globally`);
  });

  test('hyrotrader_picks.json has picks with required fields', async ({ request }) => {
    const res = await request.get(PICKS_JSON);
    expect(res.ok(), `GET picks must be 200 (got ${res.status()})`).toBe(true);

    const data = await res.json();
    expect(data.challenge, 'challenge block required').toBeTruthy();
    expect(data.picks, 'picks array required').toBeTruthy();
    expect(data.picks.length, 'at least 1 pick').toBeGreaterThanOrEqual(1);

    for (const p of data.picks) {
      expect(p.label, 'pick must have label').toBeTruthy();
      expect(p.direction, 'pick must have direction').toBeTruthy();
    }
    console.log(`  picks: ${data.picks.length} picks found`);
  });

  test('hyrotrader_enhanced_picks.json is valid', async ({ request }) => {
    const res = await request.get(ENHANCED_JSON);
    expect(res.ok(), `GET enhanced_picks must be 200 (got ${res.status()})`).toBe(true);

    const data = await res.json();
    const ts = data.generated_at || data.enhanced_at;
    expect(ts, 'generated_at or enhanced_at must exist').toBeTruthy();
    expect(data.symbols || data.picks, 'must have symbols or picks').toBeTruthy();
    console.log(`  enhanced: timestamp=${ts}`);
  });

  test('page renders fresh data with no critical JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => {
      errors.push(`PageError: ${err.message}`);
    });
    page.on('console', (msg) => {
      if (msg.type() === 'error' &&
          ['SyntaxError', 'ReferenceError', 'TypeError', 'ChunkLoadError'].some(c => msg.text().includes(c))) {
        errors.push(`ConsoleError: ${msg.text()}`);
      }
    });

    await page.goto(PAGE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    // Page title / heading
    await expect(page.getByRole('heading', { name: /HyroTrader/i }).first()).toBeVisible();

    // The "Generated" timestamp should NOT say "Apr 7"
    const body = await page.textContent('body');
    expect(body).not.toContain('Apr 7');
    expect(body).not.toContain('Fear&Greed: 11');

    // Should show "Apr 14" or current date
    expect(body).toContain('Apr 14');

    // QuanEngine panel should show symbols
    expect(body).toMatch(/symbols?\s*scanned/i);

    // No critical JS errors
    expect(errors, `JS errors: ${errors.join('; ')}`).toHaveLength(0);

    console.log('  Page renders with fresh data, no errors');
  });

  test('Table 1: QuanEngine Regime Analysis shows all 15 symbols', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    // No colspan="9" should exist
    const colspans = await page.locator('td[colspan="9"]').count();
    expect(colspans, 'colspan="9" should not exist').toBe(0);

    // Table 1 rows: should have exactly 15 symbol rows
    const quanRows = page.locator('#quan-engine-rows tr');
    const rowCount = await quanRows.count();
    expect(rowCount, `Table 1 should have 15 rows, got ${rowCount}`).toBe(15);

    // Verify every symbol appears in Table 1
    const table1Text = await page.locator('#quan-engine-card').textContent() || '';
    for (const sym of ALL_15_SYMBOLS) {
      expect(table1Text, `Table 1 missing ${sym}`).toContain(sym);
    }

    // Header should say "15 symbols scanned"
    const statusText = await page.locator('#quan-engine-status').textContent() || '';
    expect(statusText, 'Should say 15 symbols scanned').toContain('15 symbols scanned');

    // Each row should show regime (TRENDING/RANDOM/MEAN_REVERSION)
    expect(table1Text).toMatch(/TRENDING|RANDOM|MEAN_REVERSION/);

    // Should show "No consensus" for some and signal for others
    expect(table1Text).toMatch(/No consensus\s*\(\d+\/\d+\)/);

    // At least one symbol should have BUY signal
    const signalRows = await page.locator('#quan-engine-rows tr', { hasText: /BUY|SELL/ }).count();
    expect(signalRows, 'at least one symbol should have a signal').toBeGreaterThanOrEqual(1);

    console.log(`  Table 1: ${rowCount} rows, ${signalRows} with signals, all 15 symbols present`);
  });

  test('Table 2: Hide No setup works, live scan uses 15 symbols × 12 strategies', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    const checkbox = page.locator('#filter-no-setup');
    await expect(checkbox).toBeChecked();

    // Count total rows in live signal table (should be ~180 = 15 symbols × 12 strategies)
    const allRows = page.locator('#live-signal-rows tr');
    const totalRows = await allRows.count();
    expect(totalRows, `Live scan should have 140+ rows (15×12=180 max), got ${totalRows}`).toBeGreaterThanOrEqual(140);

    // With checkbox checked, no-setup rows should be hidden
    const hiddenRows = await page.locator('.no-setup-row').evaluateAll(
      rows => rows.filter(r => (r as HTMLElement).style.display === 'none').length
    );
    const visibleNoSetup = await page.locator('.no-setup-row').evaluateAll(
      rows => rows.filter(r => (r as HTMLElement).style.display !== 'none').length
    );
    console.log(`  Table 2: ${totalRows} total rows, ${hiddenRows} hidden, ${visibleNoSetup} visible no-setup`);
    expect(visibleNoSetup, 'no-setup rows should be hidden when checkbox is checked').toBe(0);

    // Verify the live scan status shows 15 symbols
    const statusText = await page.locator('#live-signals-status').textContent() || '';
    expect(statusText).toContain('Apr 14');
  });

  test('Table 2 bridge panel shows all 15 symbols with consistent data', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    const body = await page.textContent('body') || '';

    // Should show fear & greed and lookback
    expect(body).toMatch(/Fear\s*&\s*Greed\s*\d+/i);
    expect(body).toMatch(/\d+d lookback/);

    // The bridge panel in Table 2 should list all 15 symbols
    const bridgePanel = page.locator('#quan-bridge-panel');
    await expect(bridgePanel).toBeVisible();
    const panelText = await bridgePanel.textContent() || '';

    for (const sym of ALL_15_SYMBOLS) {
      expect(panelText, `Bridge panel missing ${sym}`).toContain(sym);
    }

    // Should show "approved" for risk-gated symbols
    expect(panelText).toMatch(/approved/);

    // Bridge panel and Table 1 should show the same symbol count
    const table1Status = await page.locator('#quan-engine-status').textContent() || '';
    expect(table1Status).toContain('15 symbols');

    // Count rows in bridge panel table — should be 15
    const bridgeRows = bridgePanel.locator('tr').filter({ hasText: /USDT/ });
    const bridgeRowCount = await bridgeRows.count();
    expect(bridgeRowCount, `Bridge panel should show 15 symbol rows, got ${bridgeRowCount}`).toBe(15);

    console.log('  Bridge panel + Table 1 both show all 15 symbols');
  });
});
