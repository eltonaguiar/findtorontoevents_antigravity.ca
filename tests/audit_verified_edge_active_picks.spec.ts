/**
 * Regression: verified-edge index + getVerifiedTier must not throw; Active Picks must render.
 * See updates/2026-04-15-audit-active-picks-verified-edge-corruption.md
 *
 * Local (webServer):
 *   npx playwright test tests/audit_verified_edge_active_picks.spec.ts --project="Desktop Chrome"
 *
 * Production smoke:
 *   VERIFY_REMOTE=1 npx playwright test tests/audit_verified_edge_active_picks.spec.ts --project="Desktop Chrome"
 */
import { test, expect } from '@playwright/test';

const AUDIT = '/audit/';

const criticalPatterns = [
  'SyntaxError',
  'Unexpected token',
  'ChunkLoadError',
  'denied by modsecurity',
  'Uncaught ',
  'ReferenceError',
  'TypeError',
];

test.describe('Audit /audit/ — verified edge + Active Picks render', () => {
  test('getVerifiedTier and index are sane; Active Picks table has rows; no critical JS errors', async ({
    page,
  }) => {
    test.setTimeout(120000);
    const errors: string[] = [];
    page.on('pageerror', (err) => {
      if (/Minified React error #418|418.*HTML/.test(err.message)) return;
      errors.push(`PageError: ${err.message}`);
    });
    page.on('console', (msg) => {
      if (msg.type() !== 'error') return;
      const t = msg.text();
      if (criticalPatterns.some((p) => t.includes(p))) {
        errors.push(`ConsoleError: ${t}`);
      }
    });

    // Do not use networkidle: /audit/ polls dashboard_data.json, stock_prices, strong_signals, etc.
    await page.goto(AUDIT, { waitUntil: 'load', timeout: 90000 });
    // Tab panel may not have .active yet; rows are in DOM but not "visible" to Playwright.
    await page.waitForSelector('#tab-active table.data-table tbody tr', {
      state: 'attached',
      timeout: 120000,
    });

    const edgeOk = await page.evaluate(() => {
      const w = window as unknown as {
        getVerifiedTier?: (p: { strategy?: string; symbol?: string }) => unknown;
        _verifiedEdgeIndex?: {
          goldenCombos?: object;
          verifiedStrats?: object;
          trackCombos?: object;
          trackStrats?: object;
          stratOverallOk?: object;
        } | null;
      };
      if (typeof w.getVerifiedTier !== 'function') {
        return { ok: false, reason: 'getVerifiedTier is not a function' };
      }
      const idx = w._verifiedEdgeIndex;
      if (!idx || typeof idx !== 'object') {
        return { ok: false, reason: '_verifiedEdgeIndex is null or not an object' };
      }
      for (const k of ['goldenCombos', 'verifiedStrats', 'trackCombos', 'trackStrats', 'stratOverallOk']) {
        const v = (idx as Record<string, unknown>)[k];
        if (typeof v !== 'object' || v === null) {
          return { ok: false, reason: `_verifiedEdgeIndex.${k} missing` };
        }
      }
      try {
        const r = w.getVerifiedTier({ strategy: 'claude_gainer_1h', symbol: 'BTCUSDT' }) as {
          tier?: unknown;
        };
        if (!r || typeof r !== 'object') {
          return { ok: false, reason: 'getVerifiedTier returned non-object' };
        }
        if (!('tier' in r)) {
          return { ok: false, reason: 'getVerifiedTier result missing tier' };
        }
      } catch (e) {
        return { ok: false, reason: `getVerifiedTier threw: ${e}` };
      }
      return { ok: true as const, reason: '' };
    });
    expect(edgeOk.ok, edgeOk.reason || 'verified-edge evaluate failed').toBe(true);

    const activeRows = await page.locator('#tab-active table.data-table tbody tr').count();
    expect(
      activeRows,
      'Active Picks tab should list at least one row (embedded or JSON payload)'
    ).toBeGreaterThan(0);

    expect(errors, errors.length ? errors.join('\n') : '').toHaveLength(0);
  });

  test('Closed Picks table mirrors Active defaults: Exit, Trust/FWD delta columns, no critical JS errors', async ({
    page,
  }) => {
    test.setTimeout(120000);
    const errors: string[] = [];
    page.on('pageerror', (err) => {
      if (/Minified React error #418|418.*HTML/.test(err.message)) return;
      errors.push(`PageError: ${err.message}`);
    });
    page.on('console', (msg) => {
      if (msg.type() !== 'error') return;
      const t = msg.text();
      if (criticalPatterns.some((p) => t.includes(p))) errors.push(`ConsoleError: ${t}`);
    });
    await page.goto(AUDIT, { waitUntil: 'load', timeout: 90000 });
    await page.locator('.tab-btn[data-tab="closed"]').click();
    await page.waitForSelector('#tab-closed table.data-table thead th', { timeout: 60000 });
    const headers = await page.locator('#tab-closed table.data-table thead th').allTextContents();
    const joined = headers.join('|');
    expect(joined).toMatch(/Exit/);
    expect(joined).toMatch(/Trust/);
    expect(joined).toMatch(/FWD WR/);
    expect(joined).toMatch(/FWD N/);
    expect(joined).toMatch(/EDGE/);
    expect(errors, errors.length ? errors.join('\n') : '').toHaveLength(0);
  });
});
