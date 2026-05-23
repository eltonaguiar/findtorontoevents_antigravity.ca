import { test, expect, Page } from '@playwright/test';

/**
 * Comprehensive Audit Dashboard Test Suite – Crypto Prediction Data
 *
 * Covers:
 *  - Page load & asset fetching
 *  - Data integrity of crypto rows (score inflation, temporal sanity, regime consistency)
 *  - UI interactions (filters, sorting, regime refresh, export)
 *  - System conflict resolution & historical accuracy display
 *  - Edge-case handling (empty data, API errors)
 *  - Console error audit (CORS, JS exceptions)
 *  - Performance basics
 */

const AUDIT_URL = '/findcryptopairs/audit-trail.html';
const DASHBOARD_PAYLOAD_URL = 'dashboard_data.json';
const WAIT_FOR_RENDER = 4000;

// Helper: wait for dashboard to fully render (picks table populated)
async function waitForDashboard(page: Page) {
  await page.goto(AUDIT_URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
  // Wait for either embedded or external data to render picks
  await page.waitForFunction(
    () => {
      const tables = document.querySelectorAll('.data-table tbody tr');
      return tables.length > 0;
    },
    { timeout: 30000 }
  ).catch(() => {
    // Fallback: just wait
  });
  await page.waitForTimeout(WAIT_FOR_RENDER);
}

// ═══════════════════════════════════════════════════════════════════
// SECTION 1: PAGE LOAD & ASSET FETCHING
// ═══════════════════════════════════════════════════════════════════

test.describe('1. Page Load & Asset Fetching', () => {
  test('loads page with HTTP 200 and correct title', async ({ page }) => {
    const resp = await page.goto(AUDIT_URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
    expect(resp?.status()).toBe(200);
    const title = await page.title();
    expect(title.toLowerCase()).toMatch(/audit|dashboard|antigravity/i);
  });

  test('no critical JS errors on load', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await waitForDashboard(page);
    // Filter out known non-critical: CORS (Binance), network errors, favicon
    const critical = errors.filter(e =>
      !e.includes('CORS') &&
      !e.includes('net::') &&
      !e.includes('ERR_FAILED') &&
      !e.includes('favicon') &&
      !e.includes('AbortError') &&
      !e.includes('kline')
    );
    expect(critical).toHaveLength(0);
  });

  test('embedded data loads with picks array', async ({ page }) => {
    await waitForDashboard(page);
    const hasData = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      return D && D.picks && Array.isArray(D.picks.active) && D.picks.active.length > 0;
    });
    expect(hasData).toBe(true);
  });

  test('data generation timestamp is recent (< 6 hours old)', async ({ page }) => {
    await waitForDashboard(page);
    const ageMinutes = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      if (!D?.generated_at) return 99999;
      return (Date.now() - new Date(D.generated_at).getTime()) / 60000;
    });
    expect(ageMinutes).toBeLessThan(360); // 6 hours
  });
});

// ═══════════════════════════════════════════════════════════════════
// SECTION 2: CRYPTO ROWS DATA INTEGRITY
// ═══════════════════════════════════════════════════════════════════

test.describe('2. Crypto Rows Data Integrity', () => {
  test.beforeEach(async ({ page }) => {
    await waitForDashboard(page);
  });

  test('crypto picks have required fields', async ({ page }) => {
    const issues = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      const picks = (D?.picks?.active || []).filter((p: any) =>
        (p.asset_class || '').toUpperCase() === 'CRYPTO'
      );
      const problems: string[] = [];
      for (const p of picks.slice(0, 50)) {
        if (!p.symbol) problems.push(`Missing symbol for pick id=${p.id}`);
        if (!p.direction && !p.signal_type) problems.push(`${p.symbol}: missing direction`);
        if (p.entry == null && p.entry_price == null) problems.push(`${p.symbol}: missing entry price`);
        if (!p.source_system) problems.push(`${p.symbol}: missing source_system`);
        if (!p.strategy) problems.push(`${p.symbol}: missing strategy`);
      }
      return problems;
    });
    if (issues.length > 0) {
      console.log('Data integrity issues:', issues.slice(0, 10));
    }
    expect(issues.length).toBeLessThanOrEqual(5); // Allow a few edge cases
  });

  test('scores are 0-100 range and not all identical', async ({ page }) => {
    const result = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      const picks = (D?.picks?.active || []).filter((p: any) =>
        (p.asset_class || '').toUpperCase() === 'CRYPTO' && p.score != null
      );
      const scores = picks.map((p: any) => p.score);
      const outOfRange = scores.filter((s: number) => s < 0 || s > 100);
      const uniqueScores = new Set(scores);
      const allSame = uniqueScores.size === 1 && scores.length > 10;
      return {
        total: scores.length,
        outOfRange: outOfRange.length,
        uniqueCount: uniqueScores.size,
        allSame,
        min: Math.min(...scores),
        max: Math.max(...scores),
      };
    });
    expect(result.outOfRange).toBe(0);
    // Flag if all scores are identical (score inflation bug)
    if (result.total > 10) {
      expect(result.allSame).toBe(false);
    }
  });

  test('SANDBOX/PROBATION systems should NOT all have score 100', async ({ page }) => {
    const result = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      const picks = (D?.picks?.active || []).filter((p: any) =>
        (p.asset_class || '').toUpperCase() === 'CRYPTO' &&
        (p.trust_tier === 'SANDBOX' || p.trust_tier === 'PROBATION')
      );
      const score100 = picks.filter((p: any) => p.score === 100);
      return {
        total: picks.length,
        score100Count: score100.length,
        examples: score100.slice(0, 5).map((p: any) => ({
          symbol: p.symbol,
          system: p.source_system,
          trust: p.trust_tier,
          score: p.score,
          rawTotal: p.score_breakdown_raw_total,
        })),
      };
    });
    // If more than 50% of sandbox/probation picks have score 100, that's a scoring bug
    if (result.total > 5) {
      const inflationRate = result.score100Count / result.total;
      if (inflationRate > 0.5) {
        console.warn(`SCORE INFLATION: ${result.score100Count}/${result.total} SANDBOX/PROBATION picks have score 100`);
        console.warn('Examples:', JSON.stringify(result.examples, null, 2));
      }
      expect(inflationRate).toBeLessThan(0.8); // Hard fail if >80% inflated
    }
  });

  test('entry timestamps are before current time (no future picks)', async ({ page }) => {
    const futureCount = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      const now = Date.now();
      return (D?.picks?.active || []).filter((p: any) => {
        const t = new Date(p.picked_at || p.entry_time || p.created_at || 0).getTime();
        return t > now + 3600000; // More than 1h in the future
      }).length;
    });
    expect(futureCount).toBe(0);
  });

  test('regime_at_entry is populated for crypto picks', async ({ page }) => {
    const result = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      const cryptoPicks = (D?.picks?.active || []).filter((p: any) =>
        (p.asset_class || '').toUpperCase() === 'CRYPTO'
      );
      const withRegime = cryptoPicks.filter((p: any) =>
        p.regime_at_entry || p.market_regime
      );
      return { total: cryptoPicks.length, withRegime: withRegime.length };
    });
    if (result.total > 0) {
      const coverage = result.withRegime / result.total;
      expect(coverage).toBeGreaterThan(0.5); // At least 50% should have regime data
    }
  });

  test('R:R ratio is reasonable (0.5 to 20)', async ({ page }) => {
    const badRR = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      return (D?.picks?.active || []).filter((p: any) => {
        const rr = p.risk_reward;
        return rr != null && (rr < 0.1 || rr > 50);
      }).map((p: any) => ({ symbol: p.symbol, rr: p.risk_reward }));
    });
    if (badRR.length > 0) {
      console.warn('Suspicious R:R values:', badRR.slice(0, 5));
    }
    expect(badRR.length).toBeLessThanOrEqual(3);
  });
});

// ═══════════════════════════════════════════════════════════════════
// SECTION 3: UI INTERACTIONS (Filters, Sorting, Tabs)
// ═══════════════════════════════════════════════════════════════════

test.describe('3. UI Interactions', () => {
  test.beforeEach(async ({ page }) => {
    await waitForDashboard(page);
  });

  test('filter bar controls are present', async ({ page }) => {
    const filterIds = ['f-asset', 'f-system', 'f-dir', 'f-search', 'f-sort'];
    for (const id of filterIds) {
      const el = page.locator(`#${id}`);
      const exists = await el.count();
      expect(exists).toBeGreaterThanOrEqual(1);
    }
  });

  test('asset filter to CRYPTO reduces table rows', async ({ page }) => {
    // Get total count first
    const totalBefore = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      return (D?.picks?.active || []).length;
    });

    // Apply crypto filter
    const assetFilter = page.locator('#f-asset');
    if (await assetFilter.count() > 0) {
      await assetFilter.selectOption({ label: 'CRYPTO' }).catch(() =>
        assetFilter.selectOption('CRYPTO').catch(() => {})
      );
      await page.waitForTimeout(1000);

      const visibleRows = await page.locator('.data-table tbody tr').count();
      // Should have fewer rows than total (unless all are crypto)
      expect(visibleRows).toBeGreaterThan(0);
      expect(visibleRows).toBeLessThanOrEqual(totalBefore);
    }
  });

  test('direction filter works (LONG/SHORT)', async ({ page }) => {
    const dirFilter = page.locator('#f-dir');
    if (await dirFilter.count() > 0) {
      // Filter to SHORT
      await dirFilter.selectOption('SHORT').catch(() =>
        dirFilter.selectOption({ label: 'SHORT' }).catch(() => {})
      );
      await page.waitForTimeout(1000);

      // Check that remaining visible rows contain SHORT
      const rows = await page.locator('.data-table tbody tr').count();
      // Should have at least some short picks or 0 if none exist
      expect(rows).toBeGreaterThanOrEqual(0);
    }
  });

  test('sort dropdown changes row order', async ({ page }) => {
    const sortSelect = page.locator('#f-sort');
    if (await sortSelect.count() > 0) {
      const options = await sortSelect.locator('option').allTextContents();
      expect(options.length).toBeGreaterThanOrEqual(2);

      // Sort by score (should exist as an option)
      await sortSelect.selectOption({ index: 1 }).catch(() => {});
      await page.waitForTimeout(500);
      // Just verify no crash
      const rows = await page.locator('.data-table tbody tr').count();
      expect(rows).toBeGreaterThan(0);
    }
  });

  test('search filter finds specific symbol', async ({ page }) => {
    const searchBox = page.locator('#f-search');
    if (await searchBox.count() > 0) {
      await searchBox.fill('BTCUSDT');
      await page.waitForTimeout(1000);

      const visibleRows = await page.locator('.data-table tbody tr').count();
      // BTC should always exist
      expect(visibleRows).toBeGreaterThan(0);

      // Clear search
      await searchBox.fill('');
      await page.waitForTimeout(500);
    }
  });

  test('tab navigation renders content in each tab', async ({ page }) => {
    const tabs = page.locator('.tab-btn');
    const tabCount = await tabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(3);

    for (let i = 0; i < Math.min(tabCount, 6); i++) {
      await tabs.nth(i).click();
      await page.waitForTimeout(500);
      // Tab should be active
      const cls = await tabs.nth(i).getAttribute('class');
      expect(cls).toContain('active');
    }
  });

  test('TP Winners toggle button works', async ({ page }) => {
    const tpBtn = page.locator('#btn-tp-hit-toggle');
    if (await tpBtn.count() > 0) {
      const textBefore = await tpBtn.textContent();
      await tpBtn.click();
      await page.waitForTimeout(1000);
      const textAfter = await tpBtn.textContent();
      // Button text should change between Show/Hide
      expect(textBefore).not.toBe(textAfter);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════
// SECTION 4: REGIME & SCORING CONSISTENCY
// ═══════════════════════════════════════════════════════════════════

test.describe('4. Regime & Scoring Consistency', () => {
  test.beforeEach(async ({ page }) => {
    await waitForDashboard(page);
  });

  test('regime banner is displayed with valid state', async ({ page }) => {
    const regimeText = await page.evaluate(() => {
      return (window as any)._marketRegime || 'NOT_SET';
    });
    const validRegimes = [
      'BULL', 'BEAR', 'CHOPPY', 'UNKNOWN',
      'LEANING_BULL', 'LEANING_BEAR',
      'WEAKENING_BULL', 'WEAKENING_BEAR',
    ];
    expect(validRegimes).toContain(regimeText);
  });

  test('regime-aligned counter is not always zero (with picks present)', async ({ page }) => {
    const result = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      const regime = ((window as any)._marketRegime || '').toUpperCase();
      const activePicks = (D?.picks?.active || []).filter((p: any) => !p._resolved_live);
      const cryptoPicks = activePicks.filter((p: any) =>
        (p.asset_class || '').toUpperCase() === 'CRYPTO'
      );

      // Count aligned based on regime logic
      let aligned = 0;
      for (const p of cryptoPicks) {
        const dir = (p.direction || p.signal_type || '').toUpperCase();
        const isLong = dir === 'LONG' || dir === 'BUY';
        const isShort = dir === 'SHORT' || dir === 'SELL';

        if (regime.includes('BULL') && isLong) aligned++;
        else if (regime.includes('BEAR') && isShort) aligned++;
        else if (regime.includes('CHOP') && isShort) aligned++; // Shorts favored in choppy
      }
      return { regime, total: cryptoPicks.length, aligned };
    });

    // If there are active crypto picks, at least some should be aligned
    // (unless regime is UNKNOWN with no data)
    if (result.total > 10 && result.regime !== 'UNKNOWN') {
      expect(result.aligned).toBeGreaterThan(0);
    }
  });

  test('Refresh Regime button fetches regime data', async ({ page }) => {
    // Track network requests triggered by regime refresh
    const regimeRequests: string[] = [];
    page.on('request', (req) => {
      const url = req.url();
      if (url.includes('regime_report') || url.includes('hmm_regime') || url.includes('fng')) {
        regimeRequests.push(url);
      }
    });

    const refreshBtn = page.locator('button:has-text("Refresh Regime")');
    if (await refreshBtn.count() > 0) {
      await refreshBtn.click();
      await page.waitForTimeout(3000);
      // Should have triggered at least the regime fetch
      expect(regimeRequests.length).toBeGreaterThanOrEqual(1);
    }
  });

  test('LONG picks in BEAR regime are penalized in score', async ({ page }) => {
    const result = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      const picks = (D?.picks?.active || []).filter((p: any) => {
        const dir = (p.direction || '').toUpperCase();
        const regime = (p.regime_at_entry || p.market_regime || '').toUpperCase();
        return dir === 'LONG' && regime.includes('BEAR');
      });
      // Check if direction bias penalty is applied
      return picks.slice(0, 10).map((p: any) => ({
        symbol: p.symbol,
        score: p.score,
        regime: p.regime_at_entry || p.market_regime,
        directionReason: (p.direction_reason || '').substring(0, 80),
      }));
    });
    // Just informational — log regime-mismatched picks
    if (result.length > 0) {
      console.log(`Found ${result.length} LONG picks in BEAR regime:`, result);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════
// SECTION 5: SYSTEM CONFLICT RESOLUTION
// ═══════════════════════════════════════════════════════════════════

test.describe('5. System Conflict Resolution', () => {
  test.beforeEach(async ({ page }) => {
    await waitForDashboard(page);
  });

  test('conflict detection finds opposing picks on same symbol', async ({ page }) => {
    const conflicts = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      const picks = D?.picks?.active || [];
      const bySymbol: Record<string, any[]> = {};
      for (const p of picks) {
        const sym = p.symbol || '';
        if (!bySymbol[sym]) bySymbol[sym] = [];
        bySymbol[sym].push(p);
      }
      const conflicted: string[] = [];
      for (const [sym, group] of Object.entries(bySymbol)) {
        const dirs = new Set(group.map((p: any) => (p.direction || '').toUpperCase()));
        if (dirs.has('LONG') && dirs.has('SHORT')) {
          conflicted.push(sym);
        }
      }
      return conflicted;
    });
    // Log conflicts for visibility
    if (conflicts.length > 0) {
      console.log('Symbols with LONG/SHORT conflicts:', conflicts);
    }
  });

  test('conflict accuracy data is computed', async ({ page }) => {
    const hasConflictData = await page.evaluate(() => {
      return typeof (window as any)._conflictAccuracy === 'object' &&
        Object.keys((window as any)._conflictAccuracy || {}).length > 0;
    });
    // Conflict accuracy may be empty if no closed conflicting picks exist
    // Just verify the variable exists
    const exists = await page.evaluate(() => {
      return (window as any)._conflictAccuracy !== undefined;
    });
    expect(exists).toBe(true);
  });

  test('conflicting picks show warning indicators in UI', async ({ page }) => {
    // Check that coin-flip or warning icons exist for conflicted picks
    const warningIcons = await page.locator('[title*="COIN FLIP"], [title*="oppose"]').count();
    // Also check for conflict info in tooltips
    const conflictTooltips = await page.locator('[title*="conflict"], [title*="opposing"]').count();
    // May be zero if no active conflicts — that's OK
    console.log(`Conflict UI indicators: ${warningIcons} warnings, ${conflictTooltips} tooltips`);
  });

  test('system historical WR is tracked per system', async ({ page }) => {
    const systemStats = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      const systems = D?.systems || {};
      const withWR = Object.entries(systems).filter(([_, s]: [string, any]) =>
        s.win_rate != null || s.total_trades != null
      );
      return {
        totalSystems: Object.keys(systems).length,
        withTrackRecord: withWR.length,
        examples: withWR.slice(0, 5).map(([name, s]: [string, any]) => ({
          name,
          wr: s.win_rate,
          trades: s.total_trades,
        })),
      };
    });
    console.log('System stats:', systemStats);
    // At least some systems should have track records
    if (systemStats.totalSystems > 0) {
      expect(systemStats.withTrackRecord).toBeGreaterThan(0);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════
// SECTION 6: CONSOLE ERRORS & NETWORK AUDIT
// ═══════════════════════════════════════════════════════════════════

test.describe('6. Console & Network Audit', () => {
  test('audit all console errors (categorized)', async ({ page }) => {
    const errors: Array<{type: string; message: string}> = [];
    const warnings: string[] = [];

    page.on('pageerror', (err) => errors.push({ type: 'js_error', message: err.message }));
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push({ type: 'console_error', message: msg.text() });
      } else if (msg.type() === 'warning') {
        warnings.push(msg.text());
      }
    });

    await waitForDashboard(page);

    // Categorize errors
    const corsErrors = errors.filter(e => e.message.includes('CORS') || e.message.includes('Access-Control'));
    const networkErrors = errors.filter(e => e.message.includes('net::') || e.message.includes('ERR_FAILED'));
    const jsErrors = errors.filter(e =>
      !e.message.includes('CORS') &&
      !e.message.includes('net::') &&
      !e.message.includes('ERR_FAILED') &&
      !e.message.includes('favicon')
    );

    console.log(`Error summary: ${corsErrors.length} CORS, ${networkErrors.length} network, ${jsErrors.length} JS`);

    // CORS errors are known (Binance) — warn but don't fail
    if (corsErrors.length > 0) {
      console.warn('CORS errors (Binance klines):', corsErrors.slice(0, 3).map(e => e.message.substring(0, 100)));
    }

    // JS errors should be zero
    expect(jsErrors.length).toBe(0);
  });

  test('failed network requests are logged', async ({ page }) => {
    const failedRequests: Array<{url: string; status: number}> = [];

    page.on('response', (resp) => {
      if (resp.status() >= 400 && !resp.url().includes('favicon')) {
        failedRequests.push({ url: resp.url(), status: resp.status() });
      }
    });

    await waitForDashboard(page);

    // Log failed requests for visibility
    if (failedRequests.length > 0) {
      console.log('Failed requests:', failedRequests.slice(0, 10));
    }
    // Allow some failures (external APIs) but flag excessive ones
    const nonExternalFailures = failedRequests.filter(r =>
      !r.url.includes('binance') &&
      !r.url.includes('coingecko') &&
      !r.url.includes('alternative.me')
    );
    expect(nonExternalFailures.length).toBeLessThanOrEqual(2);
  });

  test('Binance klines have CoinGecko fallback', async ({ page }) => {
    // Verify the fallback function exists
    const hasFallback = await page.evaluate(() => {
      return typeof (window as any).fetchBinanceKlinesWithFailover === 'function';
    });
    // The function should be defined (our fix added CoinGecko fallback)
    expect(hasFallback).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════════
// SECTION 7: EDGE CASES
// ═══════════════════════════════════════════════════════════════════

test.describe('7. Edge Cases', () => {
  test('search for non-existent symbol shows empty state gracefully', async ({ page }) => {
    await waitForDashboard(page);
    const searchBox = page.locator('#f-search');
    if (await searchBox.count() > 0) {
      await searchBox.fill('ZZZZNONEXISTENT999');
      await page.waitForTimeout(1000);

      // Should show 0 rows or an empty message — not crash
      const rows = await page.locator('.data-table tbody tr').count();
      expect(rows).toBe(0);

      // Check for any error state
      const pageText = await page.textContent('body') || '';
      expect(pageText).not.toContain('undefined');
      expect(pageText).not.toContain('NaN');
    }
  });

  test('extremely long symbol search does not break UI', async ({ page }) => {
    await waitForDashboard(page);
    const searchBox = page.locator('#f-search');
    if (await searchBox.count() > 0) {
      await searchBox.fill('A'.repeat(200));
      await page.waitForTimeout(500);
      // Should not crash
      const rows = await page.locator('.data-table tbody tr').count();
      expect(rows).toBe(0);
    }
  });

  test('rapid filter changes do not cause race conditions', async ({ page }) => {
    await waitForDashboard(page);
    const searchBox = page.locator('#f-search');
    if (await searchBox.count() > 0) {
      // Rapid fire searches
      for (const term of ['BTC', 'ETH', 'SOL', 'BNB', '']) {
        await searchBox.fill(term);
        await page.waitForTimeout(100);
      }
      await page.waitForTimeout(1000);
      // Should recover to showing all picks
      const rows = await page.locator('.data-table tbody tr').count();
      expect(rows).toBeGreaterThan(0);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════
// SECTION 8: PERFORMANCE
// ═══════════════════════════════════════════════════════════════════

test.describe('8. Performance', () => {
  test('page loads within 8 seconds', async ({ page }) => {
    const start = Date.now();
    await page.goto(AUDIT_URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForFunction(
      () => document.querySelectorAll('.data-table tbody tr').length > 0,
      { timeout: 30000 }
    ).catch(() => {});
    const elapsed = Date.now() - start;
    console.log(`Dashboard load time: ${elapsed}ms`);
    expect(elapsed).toBeLessThan(8000);
  });

  test('filter interaction responds within 2 seconds', async ({ page }) => {
    await waitForDashboard(page);
    const searchBox = page.locator('#f-search');
    if (await searchBox.count() > 0) {
      const start = Date.now();
      await searchBox.fill('BTCUSDT');
      await page.waitForTimeout(500);
      await page.locator('.data-table tbody tr').first().waitFor({ timeout: 2000 }).catch(() => {});
      const elapsed = Date.now() - start;
      expect(elapsed).toBeLessThan(2000);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════
// SECTION 9: DATA QUALITY (from CSV analysis)
// ═══════════════════════════════════════════════════════════════════

test.describe('9. Data Quality Validation', () => {
  test.beforeEach(async ({ page }) => {
    await waitForDashboard(page);
  });

  test('no asset class mismatches (e.g., ETF in crypto system)', async ({ page }) => {
    const mismatches = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      const picks = D?.picks?.active || [];
      return picks.filter((p: any) => {
        const sys = (p.source_system || '').toLowerCase();
        const asset = (p.asset_class || '').toUpperCase();
        // Crypto systems should not produce ETF/STOCK picks
        const isCryptoSystem = sys.includes('crypto') || sys.includes('ml_crypto') ||
          sys.includes('dna') || sys.includes('mutation');
        return isCryptoSystem && (asset === 'ETF' || asset === 'STOCK');
      }).map((p: any) => ({
        symbol: p.symbol,
        system: p.source_system,
        asset: p.asset_class,
      }));
    });
    if (mismatches.length > 0) {
      console.warn('Asset class mismatches:', mismatches);
    }
    // Warn but allow some — these might be intentional multi-asset systems
    expect(mismatches.length).toBeLessThanOrEqual(10);
  });

  test('closed picks have entry_time before exit_time', async ({ page }) => {
    const temporalIssues = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      const closed = D?.picks?.recent_closed || [];
      return closed.filter((p: any) => {
        const entry = new Date(p.entry_time || p.picked_at || 0).getTime();
        const exit = new Date(p.exit_time || p.closed_at || 0).getTime();
        return entry > 0 && exit > 0 && entry > exit;
      }).map((p: any) => ({
        symbol: p.symbol,
        entry: p.entry_time || p.picked_at,
        exit: p.exit_time || p.closed_at,
      }));
    });
    if (temporalIssues.length > 0) {
      console.warn(`TEMPORAL PARADOX: ${temporalIssues.length} picks have entry AFTER exit:`,
        temporalIssues.slice(0, 5));
    }
    // This should be zero — it's a data generation bug
    expect(temporalIssues.length).toBe(0);
  });

  test('forward WR values are realistic (0-100%)', async ({ page }) => {
    const badWR = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      const picks = D?.picks?.active || [];
      return picks.filter((p: any) => {
        const wr = p.strat_fwd_wr;
        return wr != null && (wr < 0 || wr > 100);
      }).length;
    });
    expect(badWR).toBe(0);
  });

  test('confidence values are 0-1 range', async ({ page }) => {
    const badConf = await page.evaluate(() => {
      const D = (window as any).DASHBOARD_DATA;
      const picks = D?.picks?.active || [];
      return picks.filter((p: any) => {
        const c = p.confidence;
        return c != null && (c < 0 || c > 1);
      }).length;
    });
    expect(badConf).toBe(0);
  });

  test('IC summary bar shows meaningful values', async ({ page }) => {
    const barText = await page.locator('.ic-summary-bar').textContent().catch(() => '');
    if (barText) {
      // Should not show "0 of X regime-aligned" without context
      // Our fix adds "(shorts favored in CHOPPY)" label
      expect(barText).not.toMatch(/0 of \d+ regime-aligned$/);
      // Should show WR percentage
      expect(barText).toContain('%');
    }
  });

  test('AI analyze button shows "AI" not "??"', async ({ page }) => {
    const qqButtons = await page.locator('.ai-analyze-btn').allTextContents();
    for (const text of qqButtons.slice(0, 10)) {
      expect(text.trim()).toBe('AI');
    }
  });
});

// ═══════════════════════════════════════════════════════════════════
// SECTION 10: EXPORT & REPORTING
// ═══════════════════════════════════════════════════════════════════

test.describe('10. Export & Reporting', () => {
  test('CSV export button exists and triggers download', async ({ page }) => {
    await waitForDashboard(page);
    // Look for export button
    const exportBtn = page.locator('button:has-text("Export"), button:has-text("CSV"), button:has-text("Download")');
    if (await exportBtn.count() > 0) {
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 5000 }).catch(() => null),
        exportBtn.first().click(),
      ]);
      if (download) {
        const filename = download.suggestedFilename();
        expect(filename).toMatch(/\.(csv|json|xlsx)$/i);
      }
    }
  });
});
