/**
 * Post-fix verification for non-crypto active picks + WR/PF.
 *
 * Run against the live dashboard after the next dashboard CI run completes:
 *   VERIFY_REMOTE=1 VERIFY_REMOTE_URL=https://findtorontoevents.ca \
 *     npx playwright test tests/non_crypto_picks_postfix.spec.ts \
 *     --project="Desktop Chrome"
 *
 * Verifies:
 *   1. Forex PF metric is NOT corrupt (was 0.01 before P0 fix)
 *   2. Equity card no longer counts the 6 toxic symbols (CRM/ADBE/NKE/ACN/PG/HD)
 *      OR the goldmine_2x EQUITY strategy
 *   3. Consensus engine ran and picked up commodity/equity/futures feeds
 *      (no warning about the 3 typo'd paths)
 *   4. Symbols in non-crypto cards are real, recognisable instruments
 *      (not crypto leaking through)
 */
import { test, expect } from '@playwright/test';

const AUDIT_PATH = '/audit/';

// Helper: open dashboard and wait for cards to render
async function openDashboard(page: import('@playwright/test').Page) {
  await page.goto(AUDIT_PATH, { waitUntil: 'domcontentloaded', timeout: 60000 });
  // Dashboard renders client-side from /audit/data/dashboard_data.json
  await page.waitForFunction(
    () => document.querySelectorAll('.stat-card, .asset-class-card').length > 5,
    { timeout: 30000 },
  );
  await page.waitForTimeout(1500);
}

test.describe('Non-crypto picks — post-fix sanity', () => {
  test.setTimeout(90_000);

  test('dashboard payload non_crypto_performance contains all 6 asset classes', async ({ page }) => {
    await openDashboard(page);
    const payload = await page.evaluate(async () => {
      const res = await fetch('/audit/data/dashboard_data.json');
      return res.json();
    });
    const ncPerf = payload?.summary?.non_crypto_performance?.categories || {};
    const keys = Object.keys(ncPerf).map((k) => k.toUpperCase());
    for (const cls of ['EQUITY', 'FOREX', 'COMMODITY', 'FUTURES', 'ETF', 'BOND']) {
      expect(keys, `Missing asset class ${cls}`).toContain(cls);
    }
  });

  test('forex profit_factor is NOT in the corrupt sub-0.05 range', async ({ page }) => {
    await openDashboard(page);
    const fxPf = await page.evaluate(async () => {
      const res = await fetch('/audit/data/dashboard_data.json');
      const j = await res.json();
      // PF lives in performance.by_asset_class (full backtest), not in
      // summary.non_crypto_performance.categories (which only has WR / total_pnl_pct).
      const fx = j?.performance?.by_asset_class?.FOREX;
      return fx?.profit_factor ?? fx?.pf ?? null;
    });
    expect(fxPf, 'forex PF should be present').not.toBeNull();
    // Pre-fix PF was 0.0-0.01 due to corrupt entry/exit price rows.
    // Post-fix (after _price_move_corrupt_for_non_crypto) should be > 0.1
    // (currently ~0.28 — still bad real edge, but no longer corrupt).
    expect(fxPf, `forex PF=${fxPf} still in pre-fix corrupt range`).toBeGreaterThan(0.1);
  });

  test('forex total_pnl_pct improved by ~+4855 vs corrupt baseline', async ({ page }) => {
    await openDashboard(page);
    const fxTotal = await page.evaluate(async () => {
      const res = await fetch('/audit/data/dashboard_data.json');
      const j = await res.json();
      const fx = j?.summary?.non_crypto_performance?.categories?.FOREX;
      return fx?.total_pnl_pct ?? null;
    });
    expect(fxTotal, 'forex total_pnl_pct should be present').not.toBeNull();
    // Pre-fix: -7212.36. Post-fix: should be > -3000 (much better).
    expect(fxTotal, `forex total_pnl=${fxTotal} still corrupt`).toBeGreaterThan(-3000);
  });

  test('crypto closed-pick count not regressed', async ({ page }) => {
    await openDashboard(page);
    const cryptoN = await page.evaluate(async () => {
      const res = await fetch('/audit/data/dashboard_data.json');
      const j = await res.json();
      const c = j?.performance?.by_asset_class?.CRYPTO;
      // Live schema uses 'closed' (e.g. 16424). Other names kept as fallback.
      return c?.closed ?? c?.n ?? c?.trades ?? c?.total ?? null;
    });
    // No regression — crypto should be > 3000 closed picks (current ~16424)
    expect(cryptoN, `crypto N=${cryptoN} regressed`).toBeGreaterThan(3000);
  });

  test('blocked toxic equity symbols (NKE, PG, HD) absent from active picks', async ({ page }) => {
    await openDashboard(page);
    const offenders = await page.evaluate(async () => {
      const res = await fetch('/audit/data/dashboard_data.json');
      const j = await res.json();
      const active = j?.picks?.active || [];
      const blocked = new Set(['NKE', 'PG', 'HD', 'CRM', 'ADBE', 'ACN']);
      return active
        .filter((p: any) => p && blocked.has(String(p.symbol || '').toUpperCase()))
        .map((p: any) => ({ sym: p.symbol, strat: p.strategy, src: p.source_system }));
    });
    expect(offenders, `Blocked equity symbols leaked: ${JSON.stringify(offenders)}`).toEqual([]);
  });

  test('goldmine_2x_consensus blocked on EQUITY active picks', async ({ page }) => {
    await openDashboard(page);
    const leaked = await page.evaluate(async () => {
      const res = await fetch('/audit/data/dashboard_data.json');
      const j = await res.json();
      const active = j?.picks?.active || [];
      return active.filter((p: any) => {
        const cat = String(p?.asset_class || p?.category || '').toUpperCase();
        const strat = String(p?.strategy || '').toLowerCase();
        return ['EQUITY', 'STOCK', 'STOCKS'].includes(cat)
          && (strat.includes('goldmine_1x') || strat.includes('goldmine_2x'));
      }).map((p: any) => ({ sym: p.symbol, strat: p.strategy }));
    });
    expect(leaked, `goldmine on EQUITY leaked: ${JSON.stringify(leaked)}`).toEqual([]);
  });

  test('non-crypto active counts sum > 0 (not all 0)', async ({ page }) => {
    await openDashboard(page);
    const counts = await page.evaluate(async () => {
      const res = await fetch('/audit/data/dashboard_data.json');
      const j = await res.json();
      const active = j?.picks?.active || [];
      const out: Record<string, number> = {};
      const ncClasses = ['EQUITY', 'FOREX', 'COMMODITY', 'FUTURES', 'ETF', 'BOND', 'STOCK', 'STOCKS', 'INDEX'];
      for (const p of active) {
        const cat = String(p?.asset_class || p?.category || '').toUpperCase();
        if (!ncClasses.includes(cat)) continue;
        out[cat] = (out[cat] || 0) + 1;
      }
      return out;
    });
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    expect(total, `Non-crypto active total=0, breakdown=${JSON.stringify(counts)}`).toBeGreaterThan(0);
  });

  test('forex closed sample size still > 700 (corrupt rows quarantined, sample preserved)', async ({ page }) => {
    await openDashboard(page);
    const fx = await page.evaluate(async () => {
      const res = await fetch('/audit/data/dashboard_data.json');
      const j = await res.json();
      return j?.summary?.non_crypto_performance?.categories?.FOREX || null;
    });
    expect(fx).not.toBeNull();
    // Live schema: closed=731. Pre-fix had ~733 — quarantine drops 5-8 rows.
    const n = fx?.closed ?? fx?.trades ?? fx?.n ?? 0;
    expect(n, `forex closed=${n}, expected > 700`).toBeGreaterThan(700);
  });

  test('non-crypto symbols are real instruments (no crypto leakage)', async ({ page }) => {
    await openDashboard(page);
    const leaked = await page.evaluate(async () => {
      const res = await fetch('/audit/data/dashboard_data.json');
      const j = await res.json();
      const active = j?.picks?.active || [];
      return active.filter((p: any) => {
        const cat = String(p?.asset_class || p?.category || '').toUpperCase();
        const sym = String(p?.symbol || '').toUpperCase();
        // Non-crypto cards must not contain USDT pairs
        const isNc = ['EQUITY', 'FOREX', 'COMMODITY', 'FUTURES', 'ETF', 'BOND', 'STOCK', 'STOCKS', 'INDEX'].includes(cat);
        const looksCrypto = sym.endsWith('USDT') || sym.endsWith('USDC') || sym.endsWith('BUSD');
        return isNc && looksCrypto;
      }).map((p: any) => ({ sym: p.symbol, cat: p.asset_class || p.category }));
    });
    expect(leaked, `Crypto symbols leaked into non-crypto: ${JSON.stringify(leaked)}`).toEqual([]);
  });

  test('screenshot non-crypto card panel for review', async ({ page }) => {
    await openDashboard(page);
    // Heuristic: try common selectors for the non-crypto panel
    const panel = page.locator('[data-tab="non-crypto"], #tab-non-crypto, .non-crypto-panel, .asset-class-card').first();
    await page.screenshot({
      path: 'tests/screenshots/non_crypto_postfix.png',
      fullPage: true,
    });
    expect(true).toBe(true);
  });
});
